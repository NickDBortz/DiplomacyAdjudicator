import cv2
import numpy as np
import json
import math

IMAGE_PATH = 'sampleMap.png'

original = cv2.imread(IMAGE_PATH)
display = original.copy()

current_mask = None

with open('classic_map.json', 'r') as file:
    json_obj = json.load(file)

current_territory = ''

territories = {}
all_vertices = []

def mouse_callback(event, x, y, flags, param):
    global display, current_mask

    if event != cv2.EVENT_LBUTTONDOWN:
        return

    working = original.copy()
    h, w = working.shape[:2]

    # OpenCV requires a mask 2 pixels larger
    flood_mask = np.zeros((h+2, w+2), np.uint8)

    # Fill with a throwaway color
    cv2.floodFill(
        working,
        flood_mask,
        (x, y),
        (0, 255, 0),
        loDiff=(5, 5, 5),
        upDiff=(5, 5, 5)
    )

    # Remove OpenCV border
    current_mask = flood_mask[1:-1, 1:-1]

    overlay = original.copy()

    overlay[current_mask==1] = (0, 0, 255)

    alpha = 0.4

    display = cv2.addWeighted(
        overlay,
        alpha,
        original,
        1-alpha,
        0
    )

    contours, _ = cv2.findContours(
        current_mask,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_NONE
    )

    cv2.drawContours(
        display,
        contours,
        -1,
        (0, 255, 255),
        2
    )

    contour = max(contours, key=cv2.contourArea)

    perimeter = cv2.arcLength(contour, True)

    epsilon = 0.001*perimeter

    polygon = cv2.approxPolyDP(
        contour,
        epsilon=epsilon,
        closed=True
    )

    vertices = polygon[:, 0, :].tolist()

    cv2.fillPoly(
        display,
        [np.array(vertices, dtype=np.int32)],
        (100, 100, 255)
    )

    vertex_indices = condense_vertices(vertices)

    print(vertex_indices)

    territories[current_territory] = vertex_indices
    get_next_territory()

def condense_vertices(vertices):
    global all_vertices
    vertex_indices = []
    for vertex in vertices:
        found = False
        for i in range(len(all_vertices)):
            existing_vertex = all_vertices[i]
            dist = abs(math.sqrt((existing_vertex[0] - vertex[0])**2 + (existing_vertex[1] - vertex[1])**2))
            if dist <= 1:
                vertex_indices.append(i)
                found = True
                break
        if not found:
            all_vertices.append(vertex)
            vertex_indices.append(len(all_vertices)-1)
    return vertex_indices

def get_next_territory():
    global current_territory

    return_next = False
    for territory in json_obj['territories']:
        if current_territory == '' or return_next:
            current_territory = territory['name']
            print(f'Current Territory: {current_territory}')
            return
        if territory['name'] == current_territory:
            return_next = True
    print('Done!')

    json_obj['vertices'] = all_vertices

    for name, vertex_indices in territories.items():
        territory_obj = next((territory for territory in json_obj['territories'] if territory['name'] == name), None)
        territory_obj['vertices'] = vertex_indices

    json_string = json.dumps(json_obj, indent=4)
    with open('classic_map.json', 'w', encoding='utf-8') as file:
        file.write(json_string)

cv2.namedWindow('Map')
cv2.setMouseCallback('Map', mouse_callback)

get_next_territory()

while True:
    cv2.imshow('Map', display)

    key = cv2.waitKey(16)

    if key == 27:
        break

cv2.destroyAllWindows()