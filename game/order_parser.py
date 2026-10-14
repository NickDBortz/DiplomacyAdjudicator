from game.orders import Order, BuildOrder, DisbandOrder, HoldOrder, AdvanceOrder, SupportOrder, TransformOrder, ConvoyOrder
from game.unit import Unit
from game.enums import NORTH_COAST, SOUTH_COAST, ARMY, FLEET, BUILD, DISBAND, SPRING_RETREAT_PHASE, FALL_RETREAT_PHASE

class OrderParser:
    def __init__(self, adjudicator, game_state):
        self.adjudicator = adjudicator
        self.game_state = game_state
        self.allow_transformations = False

    def activate_transformations(self):
        self.allow_transformations = True

    def parse_order_string(self, order_string, owner=None):
        order = self._parse_order_string(order_string)
        if order is not None:
            if self.adjudicator.queue_order(order, owner):
                order.unit.set_order(order)
                return True
        return False

    def _parse_order_string(self, order_string):
        # Helper functions
        def expect_unit_type(split_order_string, idx):
            if idx < 0 or idx >= len(split_order_string):
                raise Exception()
            unit_type = split_order_string[idx]
            if unit_type not in ['A', 'F', BUILD, DISBAND]:
                raise Exception()
            return ARMY if unit_type == 'A' else FLEET if unit_type == 'F' else unit_type

        def expect_territory_abbr(split_order_string, idx, allow_coast=False):
            if idx < 0 or idx >= len(split_order_string):
                raise Exception()
            territory_abbr = split_order_string[idx]
            coast = None
            if allow_coast:
                split_terr_coast = territory_abbr.split('(')
                if len(split_terr_coast) > 1:
                    territory_abbr = split_terr_coast[0]
                    coast = split_terr_coast[1].split(')')[0]
                    if coast not in (NORTH_COAST, SOUTH_COAST):
                        raise Exception()
            terr = self.game_state.get_territory(territory_abbr)
            if terr is not None:
                return terr, coast
            raise Exception()

        def expect_order_type(split_order_string, idx):
            if idx < 0 or idx >= len(split_order_string):
                raise Exception()
            order_type = split_order_string[idx]
            if order_type not in ['H', '-', 'S', 'T', 'T(nc)', 'T(sc)', 'C', 'B']:
                raise Exception()
            return order_type

        try:
            # Split the string into parts
            split_order_string = order_string.strip().split(' ')
            idx = 0
            # Expect Unit type
            unit_type = expect_unit_type(split_order_string, idx)
            idx += 1

            if unit_type == BUILD:
                unit_type = expect_unit_type(split_order_string, idx)
                idx += 1
                territory, coast = expect_territory_abbr(split_order_string, idx, allow_coast=True)
                idx += 1
                unit = Unit(territory.owner, unit_type, territory)
                return BuildOrder(unit, territory, coast)

            if unit_type == DISBAND:
                unit_type = expect_unit_type(split_order_string, idx)
                idx += 1
                territory, _ = expect_territory_abbr(split_order_string, idx)
                idx += 1
                unit = territory.unit
                if unit is None or (unit.type != unit_type and not territory.is_coast):
                    raise Exception()
                return DisbandOrder(unit)

            # Expect Territory abbreviation
            territory, _ = expect_territory_abbr(split_order_string, idx)
            idx += 1
            # Expect Order type
            order_type = expect_order_type(split_order_string, idx)
            idx += 1

            # Get troop from territory
            phase = self.game_state.get_phase()
            if phase == SPRING_RETREAT_PHASE or phase == FALL_RETREAT_PHASE:
                unit = None
                for dislodged in self.adjudicator.gather_dislodged():
                    if dislodged.dislodged_from == territory:
                        unit = dislodged
                        break
            else:
                unit = territory.unit
            if unit is None or (unit.type != unit_type and not territory.is_coast):
                raise Exception()

            if order_type == 'H':
                return HoldOrder(unit)
            elif order_type == '-':
                dest_territory, coast = expect_territory_abbr(split_order_string, idx, allow_coast=True)
                idx += 1
                is_via_convoy = False
                if len(split_order_string) > idx+1:
                    is_via_convoy = split_order_string[idx].strip().lower() == 'via' and split_order_string[idx+1].strip().lower() == 'convoy'
                return AdvanceOrder(unit, dest_territory, coast, is_via_convoy)
            elif order_type == 'S':
                supported_order_string = ' '.join(split_order_string[idx:])
                supported_order = self._parse_order_string(supported_order_string)
                if not isinstance(supported_order, Order):
                    raise Exception()
                return SupportOrder(unit, supported_order)
            elif order_type.startswith('T') and self.allow_transformations: # This is a house rule and isn't always allowed
                split_terr_coast = order_type.split('(')
                coast = None
                if len(split_terr_coast) > 1:
                    coast = split_terr_coast[1].split(')')[0]
                    if coast not in (NORTH_COAST, SOUTH_COAST):
                        raise Exception()
                return TransformOrder(unit, coast)
            elif order_type == 'C':
                if unit_type != FLEET:
                    raise Exception()
                advance_order_string = ' '.join(split_order_string[idx:])
                advance_order = self._parse_order_string(advance_order_string)
                if not isinstance(advance_order, AdvanceOrder):
                    raise Exception()
                return ConvoyOrder(unit, advance_order.unit, advance_order.dest_territory)
            else:
                raise Exception()
        except Exception:
            return None