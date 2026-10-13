from map import Map

if __name__ == "__main__":
    map = Map()

    map.parse_order_string('A STP - LIV', map.russia)
    map.parse_order_string('A MOS S A STP - LIV', map.russia)

    map.resolve_orders()

    map.parse_order_string('A WAR - PRU', map.russia)
    map.parse_order_string('A LIV S A WAR - PRU', map.russia)

    map.parse_order_string('A BER - PRU', map.germany)

    map.parse_order_string('A EDI T', map.england)

    map.resolve_orders()

    map.render()