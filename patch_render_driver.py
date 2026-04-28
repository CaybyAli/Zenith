from pathlib import Path

file = Path(r"D:\Zenith\core\final_render_driver.py")
content = file.read_text(encoding="utf-8")

# Zoompan Filter deaktivieren
old = '''        zoom_instrs = self._find_zoom_instructions(segment, dynamic_edit_plan)
        if zoom_instrs:
            max_intensity = max(z.intensity for z in zoom_instrs)
            # intensity 0.0 → 1.0x zoom, 1.0 → 1.5x zoom (smooth zoompan)
            zoom_factor = round(1.0 + float(max_intensity) * 0.5, 3)
            frame_count = max(1, int(round(segment.duration * 30)))
            # zoompan: ramp up to zoom_factor over the whole segment length
            filters.append(
                f"zoompan="
                f"z='min(zoom+0.0015,{zoom_factor})':"
                f"d={frame_count}:"
                f"s=1920x1080:"
                f"fps=30"
            )'''

new = '''        # zoompan temporär deaktiviert (zu langsam)
        pass'''

if old in content:
    content = content.replace(old, new)
    file.write_text(content, encoding="utf-8")
    print("PATCH OK - zoompan deaktiviert!")
else:
    print("NICHT GEFUNDEN")