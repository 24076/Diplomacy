class PhaseManager:
    def next_turn(self, year: int, season: str):
        if season == "SPRING":
            return year, "FALL"
        return year + 1, "SPRING"
