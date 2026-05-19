from src.constants import logging_func, S_DATA
import pandas as pd
from os import path

logging = logging_func(__name__)

# Two-Book Architecture - Separate Holdings (Core) from Swing (Trade)
F_HOLDINGS = f"{S_DATA}holdings.csv"
F_SWING = f"{S_DATA}swing.csv"


class Rachet:
    def __init__(self, **O_SETG):
        self.strategy = O_SETG["strategy"]
        self.stop_time = O_SETG["stop_time"]
        self._removable = False
        self._tradingsymbol = O_SETG.get("tradingsymbol")
        self._token = O_SETG.get("instrument_token")
        self._rest = O_SETG.get("rest")

        # Base unit - the invariant that scales with ratchet
        self._x = O_SETG.get("quantity", 33)

        # Initialize two-book state
        self._holdings = self._load_book(F_HOLDINGS, "holdings")
        self._swing = self._load_book(F_SWING, "swing")

        print(f"Holdings: {self._holdings}")
        print(f"Swing: {self._swing}")
        print(O_SETG)

    def _load_book(self, filepath, book_type):
        """Load a separate book (holdings or swing) from CSV."""
        try:
            if path.getsize(filepath) > 0:
                df = pd.read_csv(filepath)
                if not df.empty:
                    return df.iloc[-1].to_dict()
        except Exception as e:
            logging.error(f"Error loading {book_type} book: {e}")

        # Default state based on book type
        if book_type == "holdings":
            return {
                "date": "2021-03-01",
                "price": 0.0,
                "qty": 0,
                "wap": 0.0,
                "count": 0,
            }
        else:  # swing
            return {
                "date": "2021-03-01",
                "price": 0.0,
                "qty": 0,
                "wap": 0.0,
                "count": 0,
            }

    def _save_holdings(self):
        """Save holdings (core) book."""
        pd.DataFrame([self._holdings]).to_csv(
            F_HOLDINGS, mode="a", index=False, header=not path.exists(F_HOLDINGS)
        )

    def _save_swing(self):
        """Save swing (trade) book."""
        pd.DataFrame([self._swing]).to_csv(
            F_SWING, mode="a", index=False, header=not path.exists(F_SWING)
        )


    def run(self, trades, quotes, positions):
        # INVARIANTS
        FIBO_SEQ = [1, 2, 3, 5, 8, 13, 21, 34, 55]
        DOWNTREND_THRESH = -0.05  # -5%
        UPTREND_THRESH = 0.05    # +5%
        RATCHET_FACTOR = 1.07   # 7%
        SELL_PROFIT_THRESH = 1.05 # 5% profit

        # 1. Get current market price
        cmp = quotes.get(self._tradingsymbol, 0)
        if cmp <= 0:
            print("no action because price is 0")
            return

        # 2. Load last price from holdings (our baseline)
        last_p = self._holdings.get("price", cmp)
        if last_p <= 0:
            last_p = cmp  # First run

        change = (cmp - last_p) / last_p if last_p > 0 else 0

        # Get current fibo step from swing count
        curr_step = self._swing.get("count", 0)

        # --- DOWNTREND TRIGGER (<= -5%) ---
        if change <= DOWNTREND_THRESH:
            # Calculate next fibo multiplier
            next_idx = min(curr_step + 1, len(FIBO_SEQ) - 1)
            mult = FIBO_SEQ[next_idx]
            buy_qty = int(self._x * mult)

            self._swing["date"] = pd.Timestamp.now().strftime("%Y-%m-%d")
            self._swing["price"] = cmp

            if mult == 1:
                # Add to Holdings (Core/Vault) - Fibo-1 = base unit
                old_h_qty = self._holdings.get("qty", 0)
                old_h_wap = self._holdings.get("wap", 0)
                old_h_val = old_h_qty * old_h_wap

                new_qty = old_h_qty + buy_qty
                new_wap = round((old_h_val + buy_qty * cmp) / new_qty, 2) if new_qty > 0 else cmp

                self._holdings.update({
                    "date": pd.Timestamp.now().strftime("%Y-%m-%d"),
                    "price": cmp,
                    "qty": new_qty,
                    "wap": new_wap,
                    "count": old_h_qty + buy_qty,
                })
                self._save_holdings()
                print(f"HOLDINGS BUY: {buy_qty} @ {cmp}, WAP: {new_wap}")
            else:
                # Add to Swing (Trade bucket)
                old_s_qty = self._swing.get("qty", 0)
                old_s_wap = self._swing.get("wap", 0)
                old_s_val = old_s_qty * old_s_wap

                new_s_qty = old_s_qty + buy_qty
                new_s_wap = round((old_s_val + buy_qty * cmp) / new_s_qty, 2) if new_s_qty > 0 else cmp

                self._swing.update({
                    "qty": new_s_qty,
                    "wap": new_s_wap,
                    "count": next_idx,
                })
                self._save_swing()
                print(f"SWING STACK: {buy_qty} @ {cmp}, Step: {mult}x")

        # --- UPTREND / RECOVERY TRIGGER (>= +5%) ---
        elif change >= UPTREND_THRESH:
            s_qty = self._swing.get("qty", 0)
            s_wap = self._swing.get("wap", 0)

            if s_qty > 0 and curr_step > 0:
                # SCENARIO A: SELL SWING AT PROFIT
                if cmp >= s_wap * SELL_PROFIT_THRESH:
                    profit = (cmp * s_qty) - (s_wap * s_qty)
                    self._x = int(self._x * RATCHET_FACTOR)  # Ratchet up

                    # Reset swing book
                    self._swing = {
                        "date": pd.Timestamp.now().strftime("%Y-%m-%d"),
                        "price": cmp,
                        "qty": 0,
                        "wap": 0.0,
                        "count": 0,
                    }
                    self._save_swing()
                    print(f"SWING SELL: {s_qty} @ {cmp}, Profit: {profit:.2f}, New x: {self._x}")

                # SCENARIO B: PIVOT (Weak bounce -> consolidate)
                else:
                    # Move swing to holdings + add more
                    h_qty = self._holdings.get("qty", 0)
                    h_wap = self._holdings.get("wap", 0)
                    s_val = s_qty * s_wap
                    h_val = h_qty * h_wap

                    # Additional buy
                    pivot_qty = int(self._x * 2)

                    new_h_qty = h_qty + s_qty + pivot_qty
                    new_h_wap = round((h_val + s_val + pivot_qty * cmp) / new_h_qty, 2)

                    self._holdings.update({
                        "date": pd.Timestamp.now().strftime("%Y-%m-%d"),
                        "price": cmp,
                        "qty": new_h_qty,
                        "wap": new_h_wap,
                        "count": new_h_qty,
                    })

                    # Reset swing
                    self._swing = {
                        "date": pd.Timestamp.now().strftime("%Y-%m-%d"),
                        "price": cmp,
                        "qty": 0,
                        "wap": 0.0,
                        "count": 2,  # Reset to step 2
                    }
                    self._x = int(self._x * RATCHET_FACTOR)

                    self._save_holdings()
                    self._save_swing()
                    print(f"PIVOT: Moved swing->holdings + bought {pivot_qty}, New x: {self._x}")

            # STANDARD UPTREND (no swing position, add to holdings)
            else:
                buy_qty = self._x
                old_qty = self._holdings.get("qty", 0)
                old_wap = self._holdings.get("wap", 0)
                old_val = old_qty * old_wap

                new_qty = old_qty + buy_qty
                new_wap = round((old_val + buy_qty * cmp) / new_qty, 2)

                self._holdings.update({
                    "date": pd.Timestamp.now().strftime("%Y-%m-%d"),
                    "price": cmp,
                    "qty": new_qty,
                    "wap": new_wap,
                    "count": new_qty,
                })
                self._save_holdings()
                print(f"HOLDINGS BUY: {buy_qty} @ {cmp}")

        # --- IDLE ---
        else:
            # Price within +/- 5% range - no action
            print(f"HOLD: {cmp}, change: {change*100:.2f}%")
