from game.territory import LandTerritory
from game.enums import NORTH_COAST, SOUTH_COAST, ARMY, ADVANCE, SUPPORT

class Renderer:
    def __init__(self):
        pass

    def render(self, wait=False):
        pass

class BlankRenderer(Renderer):
    def __init__(self):
        pass

class CV2Renderer(Renderer):
    def __init__(self, width, height, vertices, water_color, territory_objs, game_state):
        super().__init__()

        import cv2
        import numpy as np
        self.cv2 = cv2
        self.np = np
        
        self.width = width 
        self.height = height
        self.water_color = water_color
        self.territory_objs = territory_objs
        self.game_state = game_state

        for territory_obj in territory_objs:
            self.smooth_polygons(vertices, territory_obj)

    def smooth_polygons(self, vertices, territory_obj):
        EDGE_EPSILON = 10
        def is_edge_point(p):
            x, y = p

            return (
                x <= EDGE_EPSILON or
                y <= EDGE_EPSILON or
                x >= self.width - EDGE_EPSILON or
                y >= self.height - EDGE_EPSILON
            )

        polygons = territory_obj['polygons']
        for i in range(len(polygons)):
            pts = self.np.asarray([vertices[vertex_index] for vertex_index in polygons[i]], dtype=float)

            for _ in range(2):
                new_pts = []
                n = len(pts)
                for j in range(n):
                    p0 = pts[j]
                    p1 = pts[(j+1) % n]

                    if is_edge_point(p0) or is_edge_point(p1):
                        new_pts.append(p0)
                        continue

                    q = 0.75 * p0 + 0.25 * p1
                    r = 0.25 * p0 + 0.75 * p1

                    new_pts.extend(([q, r]))

                pts = self.np.array(new_pts)

            pts = pts.astype(self.np.int32)

            polygons[i] = pts

    def render(self, wait=False):
        self.cv2.destroyAllWindows()
        # Create canvas
        canvas = self.np.zeros((self.height, self.width, 3), dtype=self.np.uint8)

        # Render the territories and their borders and decorations
        territories = self.territory_objs
        for territory in territories:
            self._render_territory_polygons(canvas, territory)
        for territory in territories:
            self._render_territory_borders(canvas, territory)
        
        # Render the units on the territories
        for territory in territories:
            if territory['land']:
                self._render_supply_center(canvas, territory)
            self._render_unit(canvas, territory)

        # Render the orders
        orders = self.game_state.get_orders()
        self._render_orders(canvas, orders)

        # Render the text on the territories
        for territory in territories:
            self._render_text(canvas, territory)

        # Display the canvas
        self.cv2.imshow("Diplomacy", canvas)
        if wait:
            self.cv2.waitKey(0)
            self.cv2.destroyAllWindows()
        else:
            self.cv2.waitKey(1)

    def _render_orders(self, canvas, orders):
        # Render advances first
        for order in orders:
            if order.type == ADVANCE:
                # Render a red arrow in the direction of the advance
                self.cv2.arrowedLine(
                    canvas,
                    self._get_unit_pos(order.unit_territory, order.unit.type),
                    self._get_unit_pos(order.dest_territory, order.unit.type),
                    (0, 0, 255),
                    3,
                    self.cv2.LINE_AA
                )

        # Then render all other orders
        for order in orders:
            if order.type == SUPPORT:
                # If we find a match, continue
                found_match = False
                for other in orders:
                    if other.match(order.supported_order):
                        found_match = True
                        break
                if not found_match:
                    continue

                if order.supported_order.type == ADVANCE:
                    adv_start = self._get_unit_pos(order.supported_order.unit_territory, order.supported_order.unit.type)
                    adv_dest = self._get_unit_pos(order.supported_order.dest_territory, order.supported_order.unit.type)

                    dest_pos = [(adv_start[0] - adv_dest[0]) // 2 + adv_dest[0], (adv_start[1] - adv_dest[1]) // 2 + adv_dest[1]]
                else:
                    dest_pos = self._get_unit_pos(order.supported_order.unit_territory, order.supported_order.unit.type)
                # Render a red arrow in the direction of the advance
                self.cv2.arrowedLine(
                    canvas,
                    self._get_unit_pos(order.unit_territory, order.unit.type),
                    dest_pos,
                    (0, 255, 0),
                    3,
                    self.cv2.LINE_AA
                )

    def _render_territory_polygons(self, canvas, territory_obj):
        territory = self.game_state.get_territory(territory_obj['name'])
        color = self._get_color(territory)
        for polygon in territory_obj['polygons']:
            self.cv2.fillPoly(
                canvas,
                [polygon],
                color
            )

    def _render_territory_borders(self, canvas, territory_obj):
        for polygon in territory_obj['polygons']:
            self.cv2.polylines(
                canvas,
                [polygon],
                isClosed=True,
                color=(0, 0, 0),
                thickness=1
            )

    def _render_supply_center(self, canvas, territory_obj):
        territory = self.game_state.get_territory(territory_obj['name'])
        if territory.is_supply_center:
            self.cv2.circle(
                canvas,
                territory_obj['supply_center_pos'],
                5,
                (0, 173, 218),
                -1
            )
            self.cv2.circle(
                canvas,
                territory_obj['supply_center_pos'],
                5,
                (0,0,0), # (0, 173, 218),
                3
            )

    def _render_unit(self, canvas, territory_obj):
        territory = self.game_state.get_territory(territory_obj['name'])
        color = self._get_color(territory)
        if territory.unit is not None:
            if isinstance(territory, LandTerritory):    
                if territory.unit.type == ARMY:
                    pos = territory_obj['army_pos']
                    self._render_army(canvas, pos, color)
                else:
                    pos = territory_obj['coast_pos']
                    if territory.unit_coast == SOUTH_COAST:
                        pos = territory_obj['south_coast_pos']
                    self._render_fleet(canvas, pos, color)
            else:
                pos = territory_obj['fleet_pos']
                self._render_fleet(canvas, pos, color)

    def _render_army(self, canvas, pos, color):
        sq_size = 15
        pt1 = (pos[0] - (sq_size//2), pos[1] - (sq_size//2))
        pt2 = (pos[0] + (sq_size//2), pos[1] + (sq_size//2))

        b,r,g = color
        b -= 30
        r -= 30
        g -= 30

        border_thickness = 2
        self.cv2.rectangle(
            canvas,
            (pt1[0]-border_thickness, pt1[1]-border_thickness),
            (pt2[0]+border_thickness, pt2[1]+border_thickness),
            (0,0,0),
            -1
        )

        self.cv2.rectangle(
            canvas,
            pt1,
            pt2,
            (b,r,g),
            -1
        )

    def _render_fleet(self, canvas, pos, color):
        sq_size = 15
        pt1 = (pos[0] - (sq_size), pos[1] - (sq_size//2))
        pt2 = (pos[0] + (sq_size), pos[1] + (sq_size//2))

        b,r,g = color
        b -= 30
        r -= 30
        g -= 30

        border_thickness = 2
        self.cv2.rectangle(
            canvas,
            (pt1[0]-border_thickness, pt1[1]-border_thickness),
            (pt2[0]+border_thickness, pt2[1]+border_thickness),
            (0,0,0),
            -1
        )

        self.cv2.rectangle(
            canvas,
            pt1,
            pt2,
            (b,r,g),
            -1
        )

    def _render_text(self, canvas, territory_obj):
        # Render Abbreviation
        font = self.cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.5
        thickness = 2
        color = (255, 255, 255)

        outline_color = (0, 0, 0)

        line_type = self.cv2.LINE_AA

        abbr = territory_obj['abbr']
        text_size, _ = self.cv2.getTextSize(abbr, font, font_scale, thickness)
        text_w, text_h = text_size[0], text_size[1]

        text_x = territory_obj['label_pos'][0] - (text_w // 2)
        text_y = territory_obj['label_pos'][1] + (text_h // 2)

        for dx, dy in [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]:
            self.cv2.putText(
                canvas, 
                abbr, 
                (text_x+dx, text_y+dy), 
                font, 
                font_scale, 
                outline_color, 
                thickness,
                line_type
            )

        self.cv2.putText(
            canvas, 
            abbr, 
            (text_x, text_y), 
            font, 
            font_scale, 
            color, 
            thickness,
            line_type
        )

    def _get_color(self, territory):
        land_color = territory.owner.color if territory.owner is not None else '#E2C69E'
        water_color = self.water_color
        color = land_color if isinstance(territory, LandTerritory) else water_color
        return self._parse_color_string(color)

    def _parse_color_string(self, color):
        h = color.lstrip("#")
        
        # Parse R, G, B integers
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        
        # Return BGR scalar tuple (OpenCV format)
        return (b, g, r)

    def _get_unit_pos(self, t, unit_type):
        t_obj = self._get_territory_obj(t.name)
        if t_obj['land']:
            if unit_type == ARMY:
                return t_obj['army_pos']
            else:
                if len(t.north_coast) > 0:
                    if t.unit_coast == NORTH_COAST:
                        return t_obj['coast_pos']
                    else:
                        return t_obj['south_coast_pos']
                else:
                    return t_obj['coast_pos']
        else:
            return t_obj['fleet_pos']

    def _get_territory_obj(self, name):
        for territory_obj in self.territory_objs:
            if territory_obj['name'] == name:
                return territory_obj
        return None