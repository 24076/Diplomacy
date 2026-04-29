from engine.state import GameState, Unit
from engine.phase_manager import PhaseManager
from engine.order_formatter import hold, move
from engine.validation.order_validator import OrderValidator
from engine.resolution.simple_resolver import SimpleResolver

POWERS = ["AUSTRIA", "ENGLAND", "FRANCE", "GERMANY", "ITALY", "RUSSIA", "TURKEY"]

INITIAL_UNITS = {
    "VIE": Unit("AUSTRIA", "A", "VIE"),
    "BUD": Unit("AUSTRIA", "A", "BUD"),
    "TRI": Unit("AUSTRIA", "F", "TRI"),
    "LON": Unit("ENGLAND", "F", "LON"),
    "EDI": Unit("ENGLAND", "F", "EDI"),
    "LVP": Unit("ENGLAND", "A", "LVP"),
    "PAR": Unit("FRANCE", "A", "PAR"),
    "MAR": Unit("FRANCE", "A", "MAR"),
    "BRE": Unit("FRANCE", "F", "BRE"),
    "BER": Unit("GERMANY", "A", "BER"),
    "MUN": Unit("GERMANY", "A", "MUN"),
    "KIE": Unit("GERMANY", "F", "KIE"),
    "ROM": Unit("ITALY", "A", "ROM"),
    "VEN": Unit("ITALY", "A", "VEN"),
    "NAP": Unit("ITALY", "F", "NAP"),
    "MOS": Unit("RUSSIA", "A", "MOS"),
    "WAR": Unit("RUSSIA", "A", "WAR"),
    "SEV": Unit("RUSSIA", "F", "SEV"),
    "STP": Unit("RUSSIA", "F", "STP"),
    "ANK": Unit("TURKEY", "F", "ANK"),
    "CON": Unit("TURKEY", "A", "CON"),
    "SMY": Unit("TURKEY", "A", "SMY"),
}

ADJACENCY = {
    "VIE": ["BOH", "GAL", "BUD", "TRI", "TYR"],
    "BUD": ["VIE", "GAL", "RUM", "SER", "TRI"],
    "TRI": ["ADR", "VEN", "TYR", "VIE", "BUD", "SER", "ALB"],
    "LON": ["YOR", "WAL", "ENG", "NTH"],
    "EDI": ["CLY", "YOR", "NTH", "NRG"],
    "LVP": ["CLY", "YOR", "WAL", "IRI", "NAT"],
    "PAR": ["PIC", "BUR", "GAS", "BRE"],
    "MAR": ["SPA", "GAS", "BUR", "PIE", "GOL"],
    "BRE": ["PIC", "PAR", "ENG", "MID"],
    "BER": ["KIE", "PRU", "SIL", "MUN"],
    "MUN": ["RUH", "KIE", "BER", "SIL", "BOH", "TYR", "BUR"],
    "KIE": ["DEN", "HEL", "HOL", "RUH", "MUN", "BER"],
    "ROM": ["TUS", "VEN", "NAP", "TYN"],
    "VEN": ["PIE", "TYR", "TRI", "APU", "ROM", "TUS"],
    "NAP": ["ROM", "APU", "ION", "TYN"],
    "MOS": ["STP", "LVN", "WAR", "UKR", "SEV"],
    "WAR": ["PRU", "LVN", "MOS", "UKR", "GAL", "SIL"],
    "SEV": ["ARM", "BLA", "RUM", "UKR", "MOS"],
    "STP": ["BAR", "FIN", "BOT", "LVN", "MOS"],
    "ANK": ["BLA", "CON", "ARM"],
    "CON": ["BUL", "ANK", "SMY", "AEG", "BLA"],
    "SMY": ["CON", "ARM", "SYR", "AEG", "EAS"],
}

class Game:
    def __init__(self):
        self.state = GameState(units={k: Unit(v.power, v.unit_type, v.location) for k, v in INITIAL_UNITS.items()})
        self.phase_manager = PhaseManager()
        self.validator = OrderValidator(ADJACENCY)
        self.resolver = SimpleResolver()

    def get_current_phase(self):
        return f"{self.state.season} {self.state.year} {self.state.phase}"

    def get_orderable_locations(self, power_name: str):
        return [loc for loc, unit in self.state.units.items() if unit.power == power_name]

    def get_possible_orders(self, location: str):
        unit = self.state.units.get(location)
        if unit is None:
            return []
        orders = [hold(unit.unit_type, location)]
        for dst in ADJACENCY.get(location, []):
            orders.append(move(unit.unit_type, location, dst))
        return orders

    def get_all_possible_orders(self):
        return {loc: self.get_possible_orders(loc) for loc in self.state.units.keys()}

    def set_orders(self, power_name: str, orders: list[str]):
        valid = []
        for order in orders:
            ok, _ = self.validator.validate(order)
            if ok:
                valid.append(order)
        self.state.submitted_orders[power_name] = valid

    def all_orders_submitted(self):
        return all(power in self.state.submitted_orders for power in POWERS)

    def process(self):
        all_orders = []
        for power in POWERS:
            power_orders = list(self.state.submitted_orders.get(power, []))
            issued_locs = {o.split()[1] for o in power_orders if len(o.split()) >= 2}
            for loc in self.get_orderable_locations(power):
                if loc not in issued_locs:
                    unit = self.state.units[loc]
                    power_orders.append(hold(unit.unit_type, loc))
            all_orders.extend(power_orders)

        result = self.resolver.resolve(self.state.units, all_orders)
        self.state.units = result["units"]
        self.state.submitted_orders = {}
        self.state.year, self.state.season = self.phase_manager.next_turn(self.state.year, self.state.season)
        return result["results"]
