/* global MapBuilderModel */
(function () {
    'use strict';
    const model = MapBuilderModel;
    const $ = id => document.getElementById(id);
    const ns = 'http://www.w3.org/2000/svg';
    let map = model.newMap(0, 0), selected = null, points = [], imageData = null, imageUrl = null;
    let imageWidth = 0, imageHeight = 0, draggedVertex = null, detailsChanged = false;

    function message(text, error = false) {
        $('message').textContent = text;
        $('message').style.color = error ? '#9c1c1c' : '#145c27';
    }

    function canContinue(discardPoints = false) {
        if (detailsChanged) {
            message('Apply the province details before continuing.', true); return false;
        }
        if (discardPoints && points.length) {
            message('Finish the polygon or undo its points before continuing.', true); return false;
        }
        return true;
    }

    function option(value, text) {
        const node = document.createElement('option');
        node.value = value; node.textContent = text;
        return node;
    }

    function render() {
        $('win-count').value = map.win_count;
        $('water-color').value = map.water_color;
        $('power-color').value = model.palette[map.players.length % model.palette.length];
        const powers = $('powers');
        powers.replaceChildren();
        for (const player of map.players) {
            const row = document.createElement('div'), label = document.createElement('span');
            label.textContent = player.name + ' ';
            const color = document.createElement('input');
            color.type = 'color'; color.value = player.color;
            color.setAttribute('aria-label', `Color for ${player.name}`);
            color.addEventListener('change', () => { player.color = color.value; });
            const remove = document.createElement('button');
            remove.type = 'button'; remove.textContent = 'Remove';
            remove.addEventListener('click', () => {
                if (!canContinue()) return;
                if (map.territories.some(t => t.owner === player.name)) {
                    message('Remove this power from its provinces before deleting it.', true); return;
                }
                map.players.splice(map.players.indexOf(player), 1); render();
            });
            row.append(label, color, remove); powers.append(row);
        }
        const list = $('territory');
        list.replaceChildren(option('', 'Choose a province'));
        map.territories.forEach((t, i) => list.append(option(String(i), `${t.name} (${t.abbr})`)));
        list.value = selected === null ? '' : String(map.territories.indexOf(selected));
        $('territory-fields').hidden = !selected;
        if (selected) {
            $('name').value = selected.name; $('abbr').value = selected.abbr;
            $('land').value = selected.land ? 'land' : 'water';
            $('supply').checked = selected.supply_center;
            $('owner').replaceChildren(option('', 'Unowned'));
            map.players.forEach(p => $('owner').append(option(p.name, p.name)));
            $('owner').value = selected.owner;
            const neighbors = $('neighbors');
            neighbors.replaceChildren();
            for (const other of map.territories.filter(t => t !== selected)) {
                const row = document.createElement('label');
                const check = document.createElement('input'); check.type = 'checkbox';
                check.checked = selected.adjacents.includes(other.name) || other.adjacents.includes(selected.name);
                check.setAttribute('aria-label', `Adjacent to ${other.name}`);
                const name = document.createElement('span'); name.textContent = other.name;
                const coast = document.createElement('select');
                coast.setAttribute('aria-label', `Coast for ${other.name}`);
                coast.append(option('', 'No coast'), option('north_coast', 'North'), option('south_coast', 'South'), option('both', 'Both'));
                coast.value = selected.north_coast.includes(other.name) && selected.south_coast.includes(other.name) ? 'both' :
                    selected.north_coast.includes(other.name) ? 'north_coast' :
                    selected.south_coast.includes(other.name) ? 'south_coast' : '';
                coast.disabled = !check.checked || !selected.land;
                check.addEventListener('change', () => {
                    if (!canContinue()) { check.checked = !check.checked; return; }
                    model.setAdjacency(map, selected, other, check.checked); render();
                });
                coast.addEventListener('change', () => {
                    if (!canContinue()) {
                        coast.value = selected.north_coast.includes(other.name) && selected.south_coast.includes(other.name) ? 'both' :
                            selected.north_coast.includes(other.name) ? 'north_coast' :
                                selected.south_coast.includes(other.name) ? 'south_coast' : '';
                        return;
                    }
                    selected.north_coast = selected.north_coast.filter(n => n !== other.name);
                    selected.south_coast = selected.south_coast.filter(n => n !== other.name);
                    if (coast.value === 'both') {
                        selected.north_coast.push(other.name); selected.south_coast.push(other.name);
                    } else if (coast.value) selected[coast.value].push(other.name);
                });
                row.append(check, name, coast); neighbors.append(row);
            }
        }
        draw();
    }

    function draw() {
        const svg = $('map'), zoom = Number($('zoom').value) / 100;
        $('zoom-value').textContent = `${Math.round(zoom * 100)}%`;
        svg.setAttribute('viewBox', `0 0 ${map.width || 1} ${map.height || 1}`);
        svg.setAttribute('width', map.width * zoom); svg.setAttribute('height', map.height * zoom);
        svg.replaceChildren();
        if (imageUrl) {
            const image = document.createElementNS(ns, 'image');
            image.setAttribute('href', imageUrl); image.setAttribute('width', map.width); image.setAttribute('height', map.height);
            svg.append(image);
        }
        for (const t of map.territories) {
            for (const polygon of t.polygons) {
                const shape = document.createElementNS(ns, 'polygon');
                shape.setAttribute('points', polygon.map(i => map.vertices[i].join(',')).join(' '));
                if (t === selected) shape.classList.add('selected');
                shape.addEventListener('click', () => {
                    if ($('mode').value === 'select' && canContinue(true)) { selected = t; render(); }
                });
                svg.append(shape);
            }
            if (t.label_pos) {
                const text = document.createElementNS(ns, 'text');
                text.setAttribute('x', t.label_pos[0]); text.setAttribute('y', t.label_pos[1]); text.textContent = t.abbr;
                svg.append(text);
            }
        }
        if (selected) {
            if ($('mode').value === 'move_vertex') {
                for (const index of new Set(selected.polygons.flat())) {
                    const circle = document.createElementNS(ns, 'circle');
                    circle.setAttribute('cx', map.vertices[index][0]); circle.setAttribute('cy', map.vertices[index][1]);
                    circle.setAttribute('r', 4); circle.setAttribute('fill', '#d21e1e'); svg.append(circle);
                }
            }
            const colors = { label_pos: '#111111', supply_center_pos: '#f5bf1b', army_pos: '#e13030',
                coast_pos: '#0659c9', south_coast_pos: '#942ac2', fleet_pos: '#0659c9' };
            for (const [field, color] of Object.entries(colors)) {
                if (!selected[field]) continue;
                const circle = document.createElementNS(ns, 'circle');
                circle.setAttribute('cx', selected[field][0]); circle.setAttribute('cy', selected[field][1]);
                circle.setAttribute('r', 5); circle.setAttribute('fill', color);
                const title = document.createElementNS(ns, 'title'); title.textContent = field; circle.append(title);
                svg.append(circle);
            }
        }
        if (points.length) {
            const line = document.createElementNS(ns, 'polyline');
            line.setAttribute('points', points.map(p => p.join(',')).join(' ')); svg.append(line);
        }
    }

    function download(suffix) {
        const blob = new Blob([JSON.stringify(map, null, 4) + '\n'], { type: 'application/json' });
        const url = URL.createObjectURL(blob), link = document.createElement('a');
        link.href = url; link.download = suffix; link.click();
        setTimeout(() => URL.revokeObjectURL(url), 1000);
    }

    $('image').addEventListener('change', event => {
        const file = event.target.files[0];
        event.target.value = '';
        if (!file) return;
        if (!canContinue()) return;
        const url = URL.createObjectURL(file), image = new Image();
        image.onload = () => {
            if (map.width && (image.width !== map.width || image.height !== map.height)) {
                URL.revokeObjectURL(url);
                message(`Image is ${image.width}×${image.height}; this map requires ${map.width}×${map.height}.`, true);
                return;
            }
            const canvas = document.createElement('canvas');
            canvas.width = image.width; canvas.height = image.height;
            const context = canvas.getContext('2d', { willReadFrequently: true });
            context.drawImage(image, 0, 0);
            imageData = context.getImageData(0, 0, image.width, image.height);
            imageWidth = image.width; imageHeight = image.height;
            if (imageUrl) URL.revokeObjectURL(imageUrl);
            imageUrl = url; map.width = image.width; map.height = image.height;
            message('Image loaded. Add powers and provinces, then trace or detect their shapes.'); render();
        };
        image.onerror = () => { URL.revokeObjectURL(url); message('Unable to load this image.', true); };
        image.src = url;
    });

    $('import').addEventListener('change', async event => {
        const file = event.target.files[0];
        event.target.value = '';
        if (!file) return;
        if (!canContinue(true)) return;
        if ((map.players.length || map.territories.length) && !confirm('Importing replaces the current map. Continue?')) return;
        try {
            const imported = JSON.parse(await file.text());
            if (!imported || !Array.isArray(imported.players) || !Array.isArray(imported.territories) ||
                !Array.isArray(imported.vertices) || !Number.isInteger(imported.width) || !Number.isInteger(imported.height) ||
                !/^#[0-9a-f]{6}$/i.test(imported.water_color) || !Number.isInteger(imported.win_count) ||
                imported.players.some(p => !p || typeof p.name !== 'string' || !/^#[0-9a-f]{6}$/i.test(p.color)) ||
                imported.vertices.some(p => !Array.isArray(p) || p.length !== 2 || !p.every(Number.isFinite)) ||
                imported.territories.some(t => !t || typeof t.name !== 'string' || typeof t.abbr !== 'string' ||
                    typeof t.owner !== 'string' || typeof t.land !== 'boolean' || typeof t.supply_center !== 'boolean' ||
                    ['label_pos', 'army_pos', 'coast_pos', 'south_coast_pos', 'fleet_pos', 'supply_center_pos']
                        .some(k => t[k] !== undefined && (!Array.isArray(t[k]) || t[k].length !== 2 || !t[k].every(Number.isFinite))) ||
                    ['adjacents', 'north_coast', 'south_coast'].some(k => !Array.isArray(t[k]) || t[k].some(n => typeof n !== 'string')) ||
                    !Array.isArray(t.polygons) || t.polygons.some(p => !Array.isArray(p) || p.some(i => !Number.isInteger(i) || i < 0 || i >= imported.vertices.length)))) {
                throw new Error('The file is not a supported map or draft JSON.');
            }
            if (imageUrl && (imported.width !== imageWidth || imported.height !== imageHeight)) {
                URL.revokeObjectURL(imageUrl); imageUrl = null; imageData = null;
            }
            map = imported; selected = null; points = [];
            message('Map imported. Select its reference image if you want to trace more regions.'); render();
        } catch (error) { message(`Import failed: ${error.message}`, true); }
    });

    $('win-count').addEventListener('change', () => { map.win_count = Number($('win-count').value); });
    $('water-color').addEventListener('change', () => { map.water_color = $('water-color').value; });
    $('add-power').addEventListener('click', () => {
        if (!canContinue()) return;
        const name = $('power-name').value.trim();
        if (!name || map.players.some(p => p.name === name)) { message('Enter a unique power name.', true); return; }
        map.players.push({ name, color: $('power-color').value });
        $('power-name').value = ''; message(`Added power ${name}.`); render();
    });
    $('add-territory').addEventListener('click', () => {
        if (!canContinue(true)) return;
        let n = 1;
        while (map.territories.some(t => t.name === `Province ${n}` || t.abbr === `P${n}`)) n++;
        selected = model.newTerritory(`Province ${n}`, `P${n}`);
        map.territories.push(selected); points = []; render();
        message('Edit the province details, then apply them.');
    });
    $('territory').addEventListener('change', () => {
        if (!canContinue(true)) {
            $('territory').value = selected === null ? '' : String(map.territories.indexOf(selected)); return;
        }
        selected = $('territory').value === '' ? null : map.territories[Number($('territory').value)];
        points = []; render();
    });
    $('delete-territory').addEventListener('click', () => {
        if (!canContinue(true)) return;
        if (!selected) { message('Select a province first.', true); return; }
        if (!confirm(`Delete ${selected.name} and its adjacencies?`)) return;
        for (const other of map.territories.filter(t => t !== selected)) model.setAdjacency(map, selected, other, false);
        map.territories.splice(map.territories.indexOf(selected), 1); selected = null; points = []; render();
    });
    $('update-territory').addEventListener('click', () => {
        if (!selected) return;
        const name = $('name').value.trim(), abbr = $('abbr').value.trim(), land = $('land').value === 'land';
        if (!name || !abbr || map.territories.some(t => t !== selected && (t.name === name || t.abbr === abbr))) {
            message('Province name and abbreviation must be nonempty and unique.', true); return;
        }
        if (!land && $('supply').checked) { message('A water province cannot be a supply center.', true); return; }
        if (!land && (selected.north_coast.length || selected.south_coast.length)) {
            message('Remove coast-specific adjacencies before changing this province to water.', true); return;
        }
        model.renameTerritory(map, selected, name); selected.abbr = abbr; selected.owner = $('owner').value;
        selected.land = land; selected.supply_center = $('supply').checked;
        detailsChanged = false;
        message('Province details updated.'); render();
    });
    for (const id of ['name', 'abbr', 'owner', 'land', 'supply']) {
        $(id).addEventListener('input', () => { detailsChanged = true; });
        $(id).addEventListener('change', () => { detailsChanged = true; });
    }
    function mapPoint(event) {
        const svg = $('map'), p = svg.createSVGPoint();
        p.x = event.clientX; p.y = event.clientY;
        const transformed = p.matrixTransform(svg.getScreenCTM().inverse());
        return [Math.round(transformed.x), Math.round(transformed.y)];
    }

    $('mode').addEventListener('change', draw);
    $('map').addEventListener('pointerdown', event => {
        if ($('mode').value !== 'move_vertex' || !selected || event.button !== 0) return;
        const [x, y] = mapPoint(event), radius = 10 / (Number($('zoom').value) / 100);
        let closest = radius * radius;
        for (const index of new Set(selected.polygons.flat())) {
            const [vx, vy] = map.vertices[index], distance = (x - vx) ** 2 + (y - vy) ** 2;
            if (distance <= closest) { closest = distance; draggedVertex = index; }
        }
        if (draggedVertex !== null) $('map').setPointerCapture(event.pointerId);
        else message("Drag one of the selected province's red vertices.", true);
    });
    $('map').addEventListener('pointermove', event => {
        if (draggedVertex === null) return;
        const [x, y] = mapPoint(event);
        map.vertices[draggedVertex] = [Math.max(0, Math.min(map.width, x)), Math.max(0, Math.min(map.height, y))];
        draw();
    });
    for (const type of ['pointerup', 'pointercancel']) {
        $('map').addEventListener(type, () => { draggedVertex = null; });
    }
    $('map').addEventListener('click', event => {
        const mode = $('mode').value;
        if (mode === 'select' || mode === 'move_vertex') return;
        if (!selected) { message('Select a province first.', true); return; }
        if (!imageUrl) { message('Load the reference image first.', true); return; }
        const [x, y] = mapPoint(event);
        if (x < 0 || y < 0 || x >= map.width || y >= map.height) { message('Click inside the image.', true); return; }
        if (mode === 'trace') { points.push([x, y]); draw(); return; }
        if (mode === 'region') {
            if (points.length) {
                message('Finish or undo the manual polygon before detecting a region.', true); return;
            }
            const threshold = Number($('threshold').value);
            if (!Number.isInteger(threshold) || threshold < 1 || threshold > 255) { message('Threshold must be between 1 and 255.', true); return; }
            try {
                model.addPolygon(map, selected, model.traceRegion(imageData, x, y, threshold));
                message('Region added automatically; no need to finish it. Check its outline and remove it if the image has gaps in its borders.');
            } catch (error) { message(error.message, true); }
            draw(); return;
        }
        if ((mode === 'fleet_pos' && selected.land) ||
            (['army_pos', 'coast_pos', 'south_coast_pos', 'supply_center_pos'].includes(mode) && !selected.land) ||
            (mode === 'supply_center_pos' && !selected.supply_center)) {
            message('This position is not applicable to the selected province.', true); return;
        }
        selected[mode] = [x, y]; message(`Placed ${mode} for ${selected.name}.`); draw();
    });
    $('finish').addEventListener('click', () => {
        if (!selected) { message('Select a province first.', true); return; }
        if (!points.length) {
            message('No manual outline is in progress. Detected regions are added automatically; use Trace polygon points to draw one manually.'); return;
        }
        try { model.addPolygon(map, selected, points); points = []; message('Polygon added.'); draw(); }
        catch (error) { message(error.message, true); }
    });
    $('undo-point').addEventListener('click', () => { points.pop(); draw(); });
    $('remove-polygon').addEventListener('click', () => {
        if (!selected || !selected.polygons.length) { message('Select a province with a polygon.', true); return; }
        selected.polygons.pop(); draw();
    });
    $('zoom').addEventListener('input', draw);
    $('export').addEventListener('click', () => {
        if (!canContinue(true)) return;
        const errors = model.validate(map);
        if (errors.length) { message('Cannot export:\n' + errors.join('\n'), true); return; }
        download('new_map.json'); message('Map downloaded. Copy it to both server/data/maps and docs/data.');
    });
    $('save-draft').addEventListener('click', () => {
        if (!canContinue(true)) return;
        download('map_draft.json'); message('Draft downloaded.');
    });
    render();
})();
