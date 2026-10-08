from map import Map

if __name__ == "__main__":
    map = Map()

    print('Players:')
    for player in map.players:
        print(f'  {player}')
    print()

    print('Territories:')
    for territory in map.territories:
        print(f'  {territory}')