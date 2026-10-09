import cv2
import numpy as np
import json
import math

IMAGE_PATH = 'black_and_white_classic_map_cleaned.png'

original = cv2.imread(IMAGE_PATH)
display = original.copy()

current_mask = None

with open('classic_map.json', 'r') as file:
    json_obj = json.load(file)
selected_vertex = None

current_territory = ''
selected_polygon = None

zoom = 1.0
pan_x = 0
pan_y = 0

panning = False
pan_start_x = 0
pan_start_y = 0

def world_to_screen(x, y):
    return (
        int(x*zoom+pan_x),
        int(y*zoom+pan_y)
    )

def screen_to_world(x, y):
    return (
        int((x - pan_x) / zoom),
        int((y - pan_y) / zoom)
    )

def find_vertex(screen_x, screen_y, radius=10):
    world_x, world_y = screen_to_world(screen_x, screen_y)

    radius = radius / zoom

    for i, (vx, vy) in enumerate(json_obj['vertices']):
        dx = vx - world_x
        dy = vy - world_y

        if dx * dx + dy * dy < radius * radius:
            return i

    return None

def mouse_callback(event, x, y, flags, param):
    global display, current_mask, selected_vertex, zoom, pan_x, pan_y, panning, pan_start_x, pan_start_y, selected_polygon

    if event == cv2.EVENT_LBUTTONDOWN:
        if flags & cv2.EVENT_FLAG_SHIFTKEY:
            panning = True
            pan_start_x = x
            pan_start_y = y
        else:
            selected_vertex = find_vertex(x, y)

    elif event == cv2.EVENT_MOUSEMOVE:
        if panning:
            pan_x += x - pan_start_x
            pan_y += y - pan_start_y

            pan_start_x = x
            pan_start_y = y

        elif selected_vertex is not None:
            wx, wy = screen_to_world(x, y)
            json_obj['vertices'][selected_vertex] = [wx, wy]

    elif event == cv2.EVENT_LBUTTONUP:
        selected_vertex = None
        panning = False

    elif event == cv2.EVENT_MOUSEWHEEL:
        if flags > 0:
            zoom_factor = 1.1
        else:
            zoom_factor = 1 / 1.1

        old_world_x, old_world_y = screen_to_world(x, y)

        zoom *= zoom_factor
        zoom = max(0.1, min(10.0, zoom))

        new_screen_x = old_world_x * zoom + pan_x
        new_screen_y = old_world_y * zoom + pan_y

        pan_x += x - new_screen_x
        pan_y += y - new_screen_y

    window_h, window_w = original.shape[:2]

    display = np.zeros_like(original)
    
    scaled_w = int(original.shape[1] * zoom)
    scaled_h = int(original.shape[0] * zoom)

    scaled = cv2.resize(
        original,
        (scaled_w, scaled_h),
        interpolation=cv2.INTER_LINEAR
    )

    x1 = int(max(0, pan_x))
    y1 = int(max(0, pan_y))

    x2 = int(min(window_w, pan_x + scaled_w))
    y2 = int(min(window_h, pan_y + scaled_h))

    sx1 = int(max(0, -pan_x))
    sy1 = int(max(0, -pan_y))

    sx2 = int(sx1 + (x2 - x1))
    sy2 = int(sy1 + (y2 - y1))

    if x2 > x1 and y2 > y1:
        display[y1:y2, x1:x2] = scaled[sy1:sy2, sx1:sx2]

    for territory in json_obj['territories']:
        if selected_polygon is not None:
            overlay_pts = []
            for vertex_index in selected_polygon:
                vx, vy = json_obj['vertices'][vertex_index]
                overlay_pts.append(world_to_screen(vx, vy))

            overlay = display.copy()

            cv2.fillPoly(
                overlay,
                [np.array(overlay_pts, np.int32)],
                (0, 0, 255)
            )

            display = cv2.addWeighted(
                overlay,
                0.35,
                display,
                0.65,
                0
            )

        for polygon in territory['polygons']:
            pts = []
            off_screen = True
            for vertex_index in polygon:
                vertex = json_obj['vertices'][vertex_index]
                vx, vy = world_to_screen(vertex[0], vertex[1])
                if vx >= 0 and vy >= 0 and vx <= window_w and vy <= window_h:
                    off_screen = False
                pts.append(world_to_screen(
                    vertex[0],
                    vertex[1]
                ))

            if not off_screen:
                pts = np.array(pts, dtype=np.int32)

                cv2.polylines(
                    display,
                    [pts],
                    isClosed=True,
                    color=(0, 255, 255),
                    thickness=2
                )

                for i, (px, py) in enumerate(pts):
                    if px < 0 or py < 0 or px > window_w or py > window_h:
                        continue
                    cv2.circle(
                        display,
                        (px, py),
                        5,
                        (0, 0, 255),
                        -1
                    )

    if event == cv2.EVENT_RBUTTONDOWN:
        wx, wy = screen_to_world(x, y)

        if (
            wx < 0 or
            wy < 0 or
            wx >= original.shape[1] or
            wy >= original.shape[0]
        ):
            return

        gray = cv2.cvtColor(
            original,
            cv2.COLOR_BGR2GRAY
        )

        _, binary = cv2.threshold(
            gray,
            200,
            255,
            cv2.THRESH_BINARY
        )

        # Clicked on a border
        if binary[wy, wx] < 200:
            print('Clicked border')
            return

        working = binary.copy()

        flood_mask = np.zeros(
            (
                working.shape[0] + 2,
                working.shape[1] + 2
            ),
            np.uint8
        )

        cv2.floodFill(
            working,
            flood_mask,
            (wx, wy),
            128
        )

        territory_mask = (
            working == 128
        ).astype(np.uint8)

        contours, _ = cv2.findContours(
            territory_mask,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_NONE
        )

        if not contours:
            return

        contour = max(
            contours,
            key=cv2.contourArea
        )

        perimeter = cv2.arcLength(
            contour,
            True
        )

        polygon = cv2.approxPolyDP(
            contour,
            epsilon=0.001 * perimeter,
            closed=True
        )

        vertices = polygon[:, 0, :].tolist()

        vertex_indices = condense_vertices(
            vertices
        )

        selected_polygon = vertex_indices

        territory_obj = next(
            (
                territory
                for territory in json_obj['territories']
                if territory['name'] == current_territory
            ),
            None
        )

        territory_obj['polygons'].append(
            vertex_indices
        )

        print(
            f'{current_territory} -> '
            f'{len(vertex_indices)} vertices'
        )

def condense_vertices(vertices):
    vertex_indices = []
    for vertex in vertices:
        found = False
        for i in range(len(json_obj['vertices'])):
            existing_vertex = json_obj['vertices'][i]
            dist = abs(math.sqrt((existing_vertex[0] - vertex[0])**2 + (existing_vertex[1] - vertex[1])**2))
            if dist <= 1:
                vertex_indices.append(i)
                found = True
                break
        if not found:
            json_obj['vertices'].append(vertex)
            vertex_indices.append(len(json_obj['vertices'])-1)
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

    if key == 115:
        print('Saving...')
        json_string = json.dumps(json_obj, indent=4)
        with open('classic_map.json', 'w', encoding='utf-8') as file:
            file.write(json_string)
        print('Saved!')

    if key == 110:
        get_next_territory()

cv2.destroyAllWindows()