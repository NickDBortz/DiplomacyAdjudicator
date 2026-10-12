from map import Map

if __name__ == "__main__":
    map = Map()

    map.parse_order_string('A STP - LIV', map.russia)
    map.parse_order_string('A MOS S A STP - LIV', map.russia)

    map.render()