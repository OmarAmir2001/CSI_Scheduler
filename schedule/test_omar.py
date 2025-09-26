from constraint import Problem
import random
import math

# ============================
# المدخالات (Inputs)
# ============================

def get_user_input():
    """Dynamically get all input data from the user"""
    subjects = []
    rooms = []
    
    print("=== University Schedule Generator - Data Input ===")
    print("\nStep 1: Enter Subject Information")
    print("-----------------------------------")
    
    time_preference_options = {
        '1': {'name': 'Morning only (9:00-12:00)', 'constraint': 'morning'},
        '2': {'name': 'Afternoon only (12:00-15:00)', 'constraint': 'afternoon'},
        '3': {'name': 'No preference', 'constraint': 'any'},
        '4': {'name': 'Before 11:00', 'constraint': 'before_11'},
        '5': {'name': 'After 11:00', 'constraint': 'after_11'}
    }
    
    while True:
        print(f"\nSubject #{len(subjects) + 1}:")
        subject_id = input("Subject ID (e.g., CS101): ").strip()
        subject_name = input("Subject Name: ").strip()
        students = int(input("Number of students: "))
        professor = input("Professor name: ").strip()
        teaching_assistant = input("Teaching Assistant name (optional): ").strip()
        required_room_type = input("Required room type (lab/lecture_hall): ").strip().lower()
        day_off = input("Professor's day off (Sun/Mon/Tue/Wed/Thu or leave blank if none): ").strip()
        
        if day_off:
            day_off = day_off.capitalize()
        
        print("\nProfessor Time Preference Options:")
        for key, option in time_preference_options.items():
            print(f"  {key}. {option['name']}")
        
        pref_choice = input("Enter preference number (1-5): ").strip()
        time_preference = time_preference_options.get(pref_choice, time_preference_options['3'])['constraint']
        
        professor = normalize_name(professor)
        teaching_assistant = normalize_name(teaching_assistant) if teaching_assistant else None
        
        subject = {
            'subject_id': subject_id.upper(),
            'subject_name': subject_name,
            'students': students,
            'professor': professor,
            'teaching_assistant': teaching_assistant,
            'required_room_type': required_room_type,
            'day_off': day_off if day_off else None,
            'time_preference': time_preference
        }
        subjects.append(subject)
        
        more = input("\nAdd another subject? (y/n): ").strip().lower()
        if more != 'y':
            break
    
    print("\nStep 2: Enter Room Information")
    print("-----------------------------------")
    
    while True:
        print(f"\nRoom #{len(rooms) + 1}:")
        room_id = input("Room ID: ").strip()
        capacity = int(input("Room capacity: "))
        room_type = input("Room type (lab/lecture_hall): ").strip().lower()
        
        room = {
            'room_id': room_id.upper(),
            'capacity': capacity,
            'room_type': room_type
        }
        rooms.append(room)
        
        more = input("\nAdd another room? (y/n): ").strip().lower()
        if more != 'y':
            break
    
    return subjects, rooms

def normalize_name(name):
    """Normalize names to Title Case for consistency"""
    return ' '.join(word.capitalize() for word in name.split())

def generate_time_slots(days=['Sun', 'Mon', 'Tue', 'Wed', 'Thu']):
    """Generate time slots for scheduling"""
    time_slots = []
    start_hour = 9.0
    end_hour = 15.0
    slot_duration = 1.5
    num_slots = int((end_hour - start_hour) / slot_duration)
    
    random.shuffle(days)
    
    for day in days:
        current_time = start_hour
        for i in range(num_slots):
            start_time = current_time
            end_time = current_time + slot_duration
            start_str = format_time(start_time)
            end_str = format_time(end_time)
            time_slot = f"{day}_{start_str}-{end_str}"
            time_slots.append(time_slot)
            current_time = end_time
    
    return time_slots

def format_time(hour_float):
    """Format time as a string"""
    hours = int(hour_float)
    minutes = int((hour_float - hours) * 60)
    return f"{hours}:{minutes:02d}"

# ============================
# القوانين (Constraints)
# ============================

def create_scheduler(subjects, rooms):
    """Create a scheduler with all constraints"""
    time_slots = generate_time_slots()
    random.shuffle(time_slots)
    
    problem = Problem()
    
    # Split subjects if needed
    all_subjects = []
    for subject in subjects:
        split_groups = split_subject_if_needed(subject, rooms)
        all_subjects.extend(split_groups)
    
    # Add variables with constraints
    for subject in all_subjects:
        suitable_rooms = [room['room_id'] for room in rooms 
                         if room['capacity'] >= subject['students']]
        
        if not suitable_rooms:
            closest_room = min(rooms, key=lambda r: abs(r['capacity'] - subject['students']))
            suitable_rooms = [closest_room['room_id']]
        
        available_slots = time_slots.copy()
        
        # Apply day off constraint
        if subject.get('day_off'):
            available_slots = [slot for slot in available_slots 
                             if slot.split('_')[0].lower() != subject['day_off'].lower()]
        
        # Apply time preference constraint
        if subject.get('time_preference') != 'any':
            available_slots = [slot for slot in available_slots 
                             if check_time_preference(slot, subject['time_preference'])]
        
        problem.addVariable(f"{subject['subject_id']}_time", available_slots)
        problem.addVariable(f"{subject['subject_id']}_room", suitable_rooms)
    
    # Constraint 1: No professor or teaching assistant double-booking
    professor_subjects = {}
    for subject in all_subjects:
        prof = subject['professor'].lower()
        if prof not in professor_subjects:
            professor_subjects[prof] = []
        professor_subjects[prof].append(subject['subject_id'])
        
        if subject['teaching_assistant']:
            ta = subject['teaching_assistant'].lower()
            if ta not in professor_subjects:
                professor_subjects[ta] = []
            professor_subjects[ta].append(subject['subject_id'])
    
    for person, subject_ids in professor_subjects.items():
        if len(subject_ids) > 1:
            for i in range(len(subject_ids)):
                for j in range(i + 1, len(subject_ids)):
                    subj1 = subject_ids[i]
                    subj2 = subject_ids[j]
                    problem.addConstraint(
                        lambda time1, time2: time1 != time2,
                        [f"{subj1}_time", f"{subj2}_time"]
                    )
    
    # Constraint 2: No room double-booking
    subject_ids = [s['subject_id'] for s in all_subjects]
    for i in range(len(subject_ids)):
        for j in range(i + 1, len(subject_ids)):
            subj1 = subject_ids[i]
            subj2 = subject_ids[j]
            problem.addConstraint(
                lambda time1, time2, room1, room2: 
                    not (time1 == time2 and room1 == room2),
                [f"{subj1}_time", f"{subj2}_time", f"{subj1}_room", f"{subj2}_room"]
            )
    
    # Constraint 3: Room type constraints
    for subject in all_subjects:
        if subject.get('required_room_type'):
            required_type = subject['required_room_type'].lower()
            problem.addConstraint(
                lambda room_id, rt=required_type: 
                    any(room['room_type'].lower() == rt for room in rooms if room['room_id'] == room_id),
                [f"{subject['subject_id']}_room"]
            )
    
    return problem, time_slots, all_subjects

def check_time_preference(time_slot, preference):
    """Check if a time slot matches the professor's time preference"""
    time_part = time_slot.split('_')[1]
    start_time_str = time_part.split('-')[0]
    start_time = convert_time_to_float(start_time_str)
    
    if preference == 'morning':
        return start_time < 12.0
    elif preference == 'afternoon':
        return start_time >= 12.0
    elif preference == 'before_11':
        return start_time < 11.0
    elif preference == 'after_11':
        return start_time >= 11.0
    elif preference == 'any':
        return True
    else:
        return True

def convert_time_to_float(time_str):
    """Convert time string like '9:00' to float like 9.0"""
    if ':' in time_str:
        hours, minutes = map(int, time_str.split(':'))
        return hours + minutes / 60.0
    else:
        return float(time_str)

# ============================
# Main Function
# ============================

def main():
    print("=== University Schedule Generator ===")
    print("Now with Room Capacity Splitting for Large Classes!")
    print("="*60)
    
    # Get all data from user
    subjects, rooms = get_user_input()
    
    # Create scheduler
    problem, time_slots, all_subjects = create_scheduler(subjects, rooms)
    
    # Solve the problem
    solution = problem.getSolution()
    
    if solution:
        print("Schedule generated successfully!")
        # Print schedule (implement print_schedule function as needed)
    else:
        print("No feasible schedule found!")

if __name__ == "__main__":
    main()