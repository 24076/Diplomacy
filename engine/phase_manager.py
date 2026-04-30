class PhaseManager:
    def next_phase(
        self,
        year: int,
        season: str,
        phase: str,
        has_retreats: bool = False,
        needs_adjustments: bool = False,
    ):
        if phase == "ORDERS":
            if has_retreats:
                return year, season, "RETREATS"
            return self._advance_after_movement(year, season, needs_adjustments)

        if phase == "RETREATS":
            return self._advance_after_movement(year, season, needs_adjustments)

        if phase == "ADJUSTMENTS":
            return year + 1, "SPRING", "ORDERS"

        return year, season, phase

    def _advance_after_movement(self, year: int, season: str, needs_adjustments: bool):
        if season == "SPRING":
            return year, "FALL", "ORDERS"
        if needs_adjustments:
            return year, "WINTER", "ADJUSTMENTS"
        return year + 1, "SPRING", "ORDERS"
