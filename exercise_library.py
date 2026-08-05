"""Curated exercise library for Fitness Coach: name, muscle group, which
facility it needs, an approximate MET value for calorie estimation, short
form-cues, and a link to search for a real demo video rather than a
fabricated/specific URL that might not exist or might show unsafe form.

MET (Metabolic Equivalent of Task) values are widely-cited general estimates
(consistent with how reference_ranges.py handles clinical thresholds
elsewhere in this app) -- not personalized or clinical. Calories are computed
as MET x weight_kg x duration_hours, then adjusted by an intensity
multiplier, in services/fitness_coach.py.
"""

from urllib.parse import quote

INTENSITY_MULTIPLIERS = {"Low": 0.8, "Moderate": 1.0, "High": 1.2}

MUSCLE_GROUPS = [
    "Chest", "Back", "Shoulders", "Biceps", "Triceps", "Abs / Core",
    "Quads", "Hamstrings", "Glutes", "Calves", "Full Body / Cardio",
]

EQUIPMENT_OPTIONS = ["Bodyweight", "Home", "Gym"]

EXERCISES = [
    {"name": "Push-ups", "muscle_group": "Chest", "equipment": "Bodyweight", "met": 8.0,
     "instructions": "Hands slightly wider than shoulders, body in a straight line, lower chest to just above the floor."},
    {"name": "Dumbbell Chest Press", "muscle_group": "Chest", "equipment": "Home", "met": 5.0,
     "instructions": "Lying on a bench or floor, press dumbbells up over the chest, controlled descent."},
    {"name": "Barbell Bench Press", "muscle_group": "Chest", "equipment": "Gym", "met": 5.0,
     "instructions": "Bar path over mid-chest, elbows at roughly 45 degrees, drive through the chest."},

    {"name": "Bent-over Rows", "muscle_group": "Back", "equipment": "Home", "met": 5.0,
     "instructions": "Hinge at the hips, flat back, pull dumbbells/barbell to the lower ribs."},
    {"name": "Pull-ups", "muscle_group": "Back", "equipment": "Bodyweight", "met": 8.0,
     "instructions": "Full hang to chin over the bar, control the descent."},
    {"name": "Lat Pulldown", "muscle_group": "Back", "equipment": "Gym", "met": 4.0,
     "instructions": "Pull the bar to upper chest, squeeze shoulder blades together at the bottom."},

    {"name": "Pike Push-ups", "muscle_group": "Shoulders", "equipment": "Bodyweight", "met": 6.0,
     "instructions": "Hips high in an inverted-V, lower the head toward the floor between the hands."},
    {"name": "Dumbbell Shoulder Press", "muscle_group": "Shoulders", "equipment": "Home", "met": 5.0,
     "instructions": "Press dumbbells overhead from shoulder height, avoid flaring elbows too far back."},
    {"name": "Lateral Raises", "muscle_group": "Shoulders", "equipment": "Home", "met": 3.5,
     "instructions": "Raise dumbbells out to the sides to shoulder height, slight bend in the elbows."},

    {"name": "Bicep Curls", "muscle_group": "Biceps", "equipment": "Home", "met": 3.5,
     "instructions": "Elbows pinned to your sides, curl the weight up without swinging."},
    {"name": "Chin-ups", "muscle_group": "Biceps", "equipment": "Bodyweight", "met": 8.0,
     "instructions": "Underhand grip, pull chin over the bar, control the descent."},

    {"name": "Tricep Dips", "muscle_group": "Triceps", "equipment": "Bodyweight", "met": 6.0,
     "instructions": "Using a bench or chair, lower the body by bending the elbows, push back up."},
    {"name": "Tricep Pushdown", "muscle_group": "Triceps", "equipment": "Gym", "met": 3.5,
     "instructions": "Elbows pinned at your sides, extend the cable attachment down until arms are straight."},

    {"name": "Plank", "muscle_group": "Abs / Core", "equipment": "Bodyweight", "met": 3.0,
     "instructions": "Forearms and toes on the floor, straight line from head to heels, brace the core."},
    {"name": "Crunches", "muscle_group": "Abs / Core", "equipment": "Bodyweight", "met": 3.8,
     "instructions": "Knees bent, lift shoulder blades off the floor by contracting the abs."},
    {"name": "Russian Twists", "muscle_group": "Abs / Core", "equipment": "Home", "met": 4.0,
     "instructions": "Seated, lean back slightly, rotate the torso side to side, optionally holding a weight."},
    {"name": "Cable Crunch", "muscle_group": "Abs / Core", "equipment": "Gym", "met": 3.5,
     "instructions": "Kneeling in front of a high cable, crunch down by contracting the abs, not pulling with the arms."},

    {"name": "Bodyweight Squats", "muscle_group": "Quads", "equipment": "Bodyweight", "met": 5.0,
     "instructions": "Feet shoulder-width, sit the hips back and down, keep the chest up."},
    {"name": "Barbell Squats", "muscle_group": "Quads", "equipment": "Gym", "met": 6.0,
     "instructions": "Bar on the upper back, squat to at least parallel, drive up through the whole foot."},
    {"name": "Lunges", "muscle_group": "Quads", "equipment": "Bodyweight", "met": 4.0,
     "instructions": "Step forward, lower the back knee toward the floor, push back to standing."},

    {"name": "Romanian Deadlifts", "muscle_group": "Hamstrings", "equipment": "Home", "met": 6.0,
     "instructions": "Soft knees, hinge at the hips keeping the bar/dumbbells close to the legs."},
    {"name": "Leg Curl Machine", "muscle_group": "Hamstrings", "equipment": "Gym", "met": 4.0,
     "instructions": "Curl the pad toward the glutes, control the return, avoid hips lifting off the pad."},

    {"name": "Glute Bridges", "muscle_group": "Glutes", "equipment": "Bodyweight", "met": 3.5,
     "instructions": "Feet flat, drive the hips up by squeezing the glutes, avoid arching the lower back."},
    {"name": "Hip Thrusts", "muscle_group": "Glutes", "equipment": "Home", "met": 5.0,
     "instructions": "Upper back on a bench, drive the hips up with a barbell or dumbbell across the hips."},

    {"name": "Calf Raises", "muscle_group": "Calves", "equipment": "Bodyweight", "met": 3.0,
     "instructions": "Rise onto the balls of the feet, pause briefly, lower under control."},

    {"name": "Jumping Jacks", "muscle_group": "Full Body / Cardio", "equipment": "Bodyweight", "met": 8.0,
     "instructions": "Jump feet out while raising arms overhead, then back to standing, steady rhythm."},
    {"name": "Running", "muscle_group": "Full Body / Cardio", "equipment": "Home", "met": 9.8,
     "instructions": "Moderate outdoor pace or treadmill jog, land midfoot, relaxed shoulders."},
    {"name": "Burpees", "muscle_group": "Full Body / Cardio", "equipment": "Bodyweight", "met": 8.0,
     "instructions": "Squat, kick back to a plank, push-up, jump feet in, jump up."},
    {"name": "Jump Rope", "muscle_group": "Full Body / Cardio", "equipment": "Home", "met": 11.0,
     "instructions": "Small, quick jumps on the balls of the feet, relaxed wrists turning the rope."},
]


def video_search_url(exercise_name):
    query = quote(f"how to do {exercise_name} proper form")
    return f"https://www.youtube.com/results?search_query={query}"


def exercises_for(muscle_group=None, facility="Both"):
    """facility: 'Home', 'Gym', or 'Both'. Bodyweight exercises show up for
    either, since they need no equipment."""
    results = []
    for ex in EXERCISES:
        if muscle_group and ex["muscle_group"] != muscle_group:
            continue
        if facility != "Both" and ex["equipment"] not in ("Bodyweight", facility):
            continue
        results.append(ex)
    return results


def find_exercise(name):
    return next((ex for ex in EXERCISES if ex["name"] == name), None)


def estimate_calories(exercise_name, duration_min, intensity, weight_kg):
    ex = find_exercise(exercise_name)
    if not ex or not duration_min or not weight_kg:
        return 0.0
    met = ex["met"] * INTENSITY_MULTIPLIERS.get(intensity, 1.0)
    return met * weight_kg * (duration_min / 60)
