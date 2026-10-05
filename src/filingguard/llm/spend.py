"""Spend tracking and a hard budget cap for paid LLM calls (D-024).

Every uncached call is checked before it is sent: if the running total plus a worst-case
estimate for this call would pass the hard cap, the call is refused with `BudgetExceeded`.
After the call, the real cost is computed from the API's token counts and appended to the
ledger. Cached calls cost nothing and are not recorded.
"""

import json
import os
import sys
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

PRICING_PATH = Path("config/pricing.json")
SPEND_DIR = Path("results/spend")
DEFAULT_WARN_USD = 5.0
DEFAULT_CAP_USD = 7.0
# Worst-case sizing for the pre-call check: tokens per prompt character, and the model's
# maximum output (gemini-3.8-flash output_token_limit, thinking included). Using the maximum
# keeps the cap hard: no single call can carry spend past it.
CHARS_PER_TOKEN_FLOOR = 3.0
MAX_OUTPUT_TOKENS_ESTIMATE = 65_536


class BudgetExceeded(RuntimeError):
    """Raised before a call that could take total spend past the hard cap."""


@dataclass(frozen=True)
class Price:
    input_per_1m: float
    output_per_1m: float


def price_for(model: str, on: date, pricing_path: Path = PRICING_PATH) -> Price:
    """Price in force for `model` on `on`. Raises if the model or date is not priced."""
    pricing = json.loads(Path(pricing_path).read_text(encoding="utf-8"))
    for band in pricing["models"].get(model, []):
        start = date.fromisoformat(band["from"])
        end = date.fromisoformat(band["until"]) if band["until"] else date.max
        if start <= on <= end:
            return Price(band["input"], band["output"])
    raise KeyError(f"no price for {model} on {on}; update {pricing_path}")


def usage_tokens(raw: dict[str, Any]) -> tuple[int, int]:
    """(input tokens, billed output tokens) from a response; output includes thinking."""
    usage = raw.get("usage_metadata") or {}
    prompt = usage.get("prompt_token_count") or 0
    output = (usage.get("candidates_token_count") or 0) + (usage.get("thoughts_token_count") or 0)
    return prompt, output


def call_cost(price: Price, input_tokens: int, output_tokens: int) -> float:
    return (input_tokens * price.input_per_1m + output_tokens * price.output_per_1m) / 1_000_000


class SpendLedger:
    """Append-only ledger (`ledger.jsonl`) plus a running total (`total.json`).

    Assumes one process spends at a time; runs are sequential.
    """

    def __init__(
        self,
        spend_dir: Path = SPEND_DIR,
        warn_usd: float = DEFAULT_WARN_USD,
        cap_usd: float = DEFAULT_CAP_USD,
        pricing_path: Path = PRICING_PATH,
        today: date | None = None,
    ) -> None:
        if warn_usd > cap_usd:
            raise ValueError("warning level must not exceed the hard cap")
        self.dir = Path(spend_dir)
        self.warn_usd, self.cap_usd = warn_usd, cap_usd
        self.pricing_path = pricing_path
        self._today = today

    @property
    def _total_path(self) -> Path:
        return self.dir / "total.json"

    def today(self) -> date:
        return self._today or date.today()

    def total(self) -> dict[str, Any]:
        if self._total_path.exists():
            return json.loads(self._total_path.read_text(encoding="utf-8"))
        return {"calls": 0, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0}

    def estimate(self, model: str, prompt: str) -> float:
        """Worst-case cost of one call, used for the pre-call check."""
        price = price_for(model, self.today(), self.pricing_path)
        return call_cost(price, int(len(prompt) / CHARS_PER_TOKEN_FLOOR) + 1, MAX_OUTPUT_TOKENS_ESTIMATE)

    def check(self, model: str, prompt: str) -> None:
        """Refuse the call if it could take spend past the hard cap."""
        spent = self.total()["cost_usd"]
        worst = self.estimate(model, prompt)
        if spent + worst > self.cap_usd:
            raise BudgetExceeded(
                f"spend ${spent:.4f} + worst case ${worst:.4f} for this call would pass the "
                f"${self.cap_usd:.2f} cap; stopping"
            )

    def record(self, model: str, raw: dict[str, Any], cache_key: str, purpose: str | None = None) -> float:
        """Log one paid call and update the running total. Returns its cost."""
        input_tokens, output_tokens = usage_tokens(raw)
        price = price_for(model, self.today(), self.pricing_path)
        cost = call_cost(price, input_tokens, output_tokens)
        before = self.total()
        after = {
            "calls": before["calls"] + 1,
            "input_tokens": before["input_tokens"] + input_tokens,
            "output_tokens": before["output_tokens"] + output_tokens,
            "cost_usd": round(before["cost_usd"] + cost, 6),
            "warn_usd": self.warn_usd,
            "cap_usd": self.cap_usd,
            "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        self.dir.mkdir(parents=True, exist_ok=True)
        entry = {
            "time": after["updated"], "model": model, "purpose": purpose, "cache_key": cache_key,
            "input_tokens": input_tokens, "output_tokens": output_tokens,
            "price_per_1m": [price.input_per_1m, price.output_per_1m], "cost_usd": round(cost, 6),
            "running_total_usd": after["cost_usd"],
        }
        with (self.dir / "ledger.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
        tmp = self._total_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(after, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, self._total_path)
        if before["cost_usd"] < self.warn_usd <= after["cost_usd"]:
            print(f"WARNING: LLM spend ${after['cost_usd']:.2f} has passed ${self.warn_usd:.2f}", file=sys.stderr)
        return cost


def ledger_from_env() -> SpendLedger:
    """Ledger with caps from `.env` (SPEND_WARN_USD, SPEND_CAP_USD), defaulting to $5 / $7."""
    warn = float(os.environ.get("SPEND_WARN_USD", DEFAULT_WARN_USD))
    cap = float(os.environ.get("SPEND_CAP_USD", DEFAULT_CAP_USD))
    if cap > DEFAULT_CAP_USD:
        raise ValueError(f"SPEND_CAP_USD {cap} is above the approved ${DEFAULT_CAP_USD:.2f}")
    return SpendLedger(warn_usd=warn, cap_usd=cap)
