"""Builds a simple, stylized front-view human figure as an SVG string, used
by Fitness Coach to show which muscle groups have been worked recently.

This is a hand-built SVG (not AI-generated) so it can be genuinely
interactive-ish (hoverable regions with tooltips) and cheaply re-colored per
render -- an AI image/GIF can't be targeted region-by-region like this.
Front-view only: Chest, Shoulders, Biceps, Abs/Core, Quads, and Calves get
their own shape; the posterior groups (Back, Triceps, Glutes, Hamstrings)
aren't visible from the front and are shown as badges alongside the figure
by the caller instead.

Body width scales by BMI category and shoulder/hip proportions shift
slightly by sex -- simple parameter changes, not separate hand-drawn
variants, and everything stays a plain stylized silhouette, never
photorealistic.
"""

NEUTRAL_FILL = "#3a3f55"
OUTLINE = "#8890a8"

BMI_SCALE = {"Underweight": 0.85, "Normal": 1.0, "Overweight": 1.15, "Obese": 1.3}

FRONT_VISIBLE_GROUPS = ["Chest", "Shoulders", "Biceps", "Abs / Core", "Quads", "Calves"]
BACK_ONLY_GROUPS = ["Back", "Triceps", "Glutes", "Hamstrings"]


def _region(shape_svg, muscle_group, highlighted):
    color = highlighted.get(muscle_group, NEUTRAL_FILL) if highlighted else NEUTRAL_FILL
    return f'<g><title>{muscle_group}</title>{shape_svg.format(fill=color)}</g>'


def build_svg(sex="Male", bmi_category="Normal", highlighted=None, width=220, height=460):
    scale = BMI_SCALE.get(bmi_category, 1.0)
    is_female = sex == "Female"

    shoulder_rx = (20 if is_female else 26) * scale
    hip_width = (66 if is_female else 56) * scale
    chest_width = (60 if is_female else 68) * scale
    cx = 110

    parts = [f'<svg viewBox="0 0 220 460" width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">']

    # Head + neck (not a tracked muscle group, always neutral)
    parts.append(f'<circle cx="{cx}" cy="34" r="22" fill="{NEUTRAL_FILL}" stroke="{OUTLINE}" stroke-width="1.5"/>')
    parts.append(f'<rect x="{cx-10}" y="52" width="20" height="16" fill="{NEUTRAL_FILL}" stroke="{OUTLINE}" stroke-width="1.5"/>')

    # Shoulders
    parts.append(_region(
        f'<ellipse cx="{cx-46}" cy="88" rx="{shoulder_rx}" ry="16" fill="{{fill}}" stroke="{OUTLINE}" stroke-width="1.5"/>',
        "Shoulders", highlighted,
    ))
    parts.append(_region(
        f'<ellipse cx="{cx+46}" cy="88" rx="{shoulder_rx}" ry="16" fill="{{fill}}" stroke="{OUTLINE}" stroke-width="1.5"/>',
        "Shoulders", highlighted,
    ))

    # Chest
    parts.append(_region(
        f'<rect x="{cx-chest_width/2:.0f}" y="76" width="{chest_width:.0f}" height="62" rx="18" '
        f'fill="{{fill}}" stroke="{OUTLINE}" stroke-width="1.5"/>',
        "Chest", highlighted,
    ))

    # Abs / core
    abs_width = 46 * scale
    parts.append(_region(
        f'<rect x="{cx-abs_width/2:.0f}" y="136" width="{abs_width:.0f}" height="52" rx="10" '
        f'fill="{{fill}}" stroke="{OUTLINE}" stroke-width="1.5"/>',
        "Abs / Core", highlighted,
    ))

    # Biceps (upper arms) -- also stands in for forearms visually, both fall under "Biceps" front-view
    bicep_rx = 15 * scale
    parts.append(_region(
        f'<ellipse cx="{cx-46}" cy="130" rx="{bicep_rx:.0f}" ry="34" fill="{{fill}}" stroke="{OUTLINE}" stroke-width="1.5"/>',
        "Biceps", highlighted,
    ))
    parts.append(_region(
        f'<ellipse cx="{cx+46}" cy="130" rx="{bicep_rx:.0f}" ry="34" fill="{{fill}}" stroke="{OUTLINE}" stroke-width="1.5"/>',
        "Biceps", highlighted,
    ))
    parts.append(_region(
        f'<ellipse cx="{cx-42}" cy="196" rx="{bicep_rx*0.85:.0f}" ry="30" fill="{{fill}}" stroke="{OUTLINE}" stroke-width="1.5"/>',
        "Biceps", highlighted,
    ))
    parts.append(_region(
        f'<ellipse cx="{cx+42}" cy="196" rx="{bicep_rx*0.85:.0f}" ry="30" fill="{{fill}}" stroke="{OUTLINE}" stroke-width="1.5"/>',
        "Biceps", highlighted,
    ))

    # Hips/waist connector (neutral, not itself a tracked group in front view)
    parts.append(f'<rect x="{cx-hip_width/2:.0f}" y="184" width="{hip_width:.0f}" height="28" rx="14" '
                  f'fill="{NEUTRAL_FILL}" stroke="{OUTLINE}" stroke-width="1.5"/>')

    # Quads
    quad_rx = 20 * scale
    parts.append(_region(
        f'<ellipse cx="{cx-22}" cy="270" rx="{quad_rx:.0f}" ry="54" fill="{{fill}}" stroke="{OUTLINE}" stroke-width="1.5"/>',
        "Quads", highlighted,
    ))
    parts.append(_region(
        f'<ellipse cx="{cx+22}" cy="270" rx="{quad_rx:.0f}" ry="54" fill="{{fill}}" stroke="{OUTLINE}" stroke-width="1.5"/>',
        "Quads", highlighted,
    ))

    # Calves
    calf_rx = 15 * scale
    parts.append(_region(
        f'<ellipse cx="{cx-22}" cy="368" rx="{calf_rx:.0f}" ry="42" fill="{{fill}}" stroke="{OUTLINE}" stroke-width="1.5"/>',
        "Calves", highlighted,
    ))
    parts.append(_region(
        f'<ellipse cx="{cx+22}" cy="368" rx="{calf_rx:.0f}" ry="42" fill="{{fill}}" stroke="{OUTLINE}" stroke-width="1.5"/>',
        "Calves", highlighted,
    ))

    # Feet
    parts.append(f'<ellipse cx="{cx-22}" cy="426" rx="14" ry="8" fill="{NEUTRAL_FILL}" stroke="{OUTLINE}" stroke-width="1.5"/>')
    parts.append(f'<ellipse cx="{cx+22}" cy="426" rx="14" ry="8" fill="{NEUTRAL_FILL}" stroke="{OUTLINE}" stroke-width="1.5"/>')

    parts.append('</svg>')
    return "".join(parts)
