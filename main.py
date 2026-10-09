from map import Map

if __name__ == "__main__":
    map = Map()

    map.parse_order_string('A STP T', map.russia)

    map.render()