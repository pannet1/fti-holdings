import logging
from typing import Any, Dict, List, Optional

import pendulum as pdlm

logger = logging.getLogger(__name__)


class ManageCandleHandler:

    def __init__(self, minute: int = 1, start: str = "09:00", stop: str = "15:30") -> None:
        self._minute = minute
        parts_s = start.split(":")
        parts_e = stop.split(":")
        self._open = pdlm.today("Asia/Kolkata").at(int(parts_s[0]), int(parts_s[1]), 0)
        self._close = pdlm.today("Asia/Kolkata").at(int(parts_e[0]), int(parts_e[1]), 0)
        self._close_times: List[pdlm.DateTime] = self._generate()
        self._last_announced_idx: int = -1

    def _generate(self) -> List[pdlm.DateTime]:
        times: List[pdlm.DateTime] = []
        cur = self._open
        while cur < self._close:
            nxt = cur.add(minutes=self._minute)
            if nxt <= self._close:
                times.append(nxt)
            else:
                if cur < self._close:
                    times.append(self._close)
                break
            cur = nxt
        return times

    def _is_truncated(self, idx: int) -> bool:
        if idx < 0 or idx >= len(self._close_times):
            return False
        if idx == 0:
            duration = (self._close_times[0] - self._open).in_minutes()
        else:
            duration = (self._close_times[idx] - self._close_times[idx - 1]).in_minutes()
        return duration < self._minute

    def force_index(self, idx: int) -> None:
        self._forced_index = idx

    @property
    def current_index(self) -> int:
        if hasattr(self, '_forced_index'):
            return self._forced_index
        now = pdlm.now("Asia/Kolkata")
        idx = -1
        for i, t in enumerate(self._close_times):
            if now >= t:
                idx = i
            else:
                break
        return idx

    def check_close(self) -> Optional[Dict[str, Any]]:
        curr = self.current_index
        if curr <= self._last_announced_idx:
            return None
        self._last_announced_idx = curr
        close_time = self._close_times[curr]
        return {
            "index": curr,
            "close_time": close_time.format("YYYY-MM-DD HH:mm:ss"),
            "is_truncated": self._is_truncated(curr),
        }
