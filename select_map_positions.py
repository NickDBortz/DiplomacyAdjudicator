import cv2
import numpy as np
import json
import math

IMAGE_PATH = 'black_and_white_classic_map2.webp'

original = cv2.imread(IMAGE_PATH)
display = original.copy()

with open('classic_map.json', 'r') as file:
    json_obj = json.load(file)

include_land = True
include_water = False
select_mode = 'supply_center_pos'
current_territory = ''

for territory in json_obj['territories']:
    if include_land and territory['land'] or include_water and not territory['land']:
        territory[select_mode] = [0, 0]

def mouse_callback(event, x, y, flags, param):
    global current_territory, display

    display = original.copy()
    for territory in json_obj['territories']:
        if include_land and territory['land'] or include_water and not territory['land']:
            pos = territory[select_mode]
            if pos[0] != 0 and pos[1] != 0:
                cv2.circle(
                    display,
                    (pos[0], pos[1]),
                    5,
                    (0, 0, 255),
                    -1
                )

    if event == cv2.EVENT_LBUTTONDOWN:  
        pos = [x, y]
        territory_obj = next((territory for territory in json_obj['territories'] if territory['name'] == current_territory), None)
        territory_obj[select_mode] = pos
        print(f'Pos: {pos[0]}, {pos[1]}')

def get_next_territory():
    global current_territory

    return_next = False
    for territory in json_obj['territories']:
        if current_territory == '' or return_next:
            if include_land and territory['land'] or include_water and not territory['land']:
                current_territory = territory['name']
                print(f'Current Territory: {current_territory}')
                return
        if territory['name'] == current_territory:
            return_next = True
    print('Done!')

cv2.namedWindow('Map')
cv2.setMouseCallback('Map', mouse_callback)

get_next_territory()

while True:
    cv2.imshow('Map', display)

    key = cv2.waitKey(16)

    if key == 27:
        break

    if key == 115:
        print('Saving...')
        json_string = json.dumps(json_obj, indent=4)
        with open('classic_map.json', 'w', encoding='utf-8') as file:
            file.write(json_string)
        print('Saved!')

    if key == 110:
        get_next_territory()

cv2.destroyAllWindows()