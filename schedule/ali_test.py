from constraint import Problem
import random
import math

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
        
        subject = {
            'subject_id': subject_id.upper(),
            'subject_name': subject_name,
            'students': students,
            'professor': professor,
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

def split_subject_if_needed(subject, rooms):
    """
    Split a subject into multiple groups if no single room can accommodate all students.
    Returns a list of subject groups.
    """
    max_room_capacity = max(room['capacity'] for room in rooms)
    
    if subject['students'] <= max_room_capacity:
        # No splitting needed
        return [subject]
    
    # Calculate how many groups we need
    groups_needed = math.ceil(subject['students'] / max_room_capacity)
    students_per_group = math.ceil(subject['students'] / groups_needed)
    
    print(f"NOTE: Subject {subject['subject_id']} has {subject['students']} students.")
    print(f"      Splitting into {groups_needed} groups of ~{students_per_group} students each.")
    
    subject_groups = []
    for i in range(groups_needed):
        group_subject = subject.copy()
        group_subject['subject_id'] = f"{subject['subject_id']}_G{i+1}"
        group_subject['students'] = students_per_group if i < groups_needed - 1 else subject['students'] - (students_per_group * (groups_needed - 1))
        group_subject['is_split_group'] = True
        group_subject['original_subject_id'] = subject['subject_id']
        group_subject['group_number'] = i + 1
        group_subject['total_groups'] = groups_needed
        subject_groups.append(group_subject)
    
    return subject_groups

def create_basic_scheduler(subjects, rooms):
    """Create scheduler with room capacity splitting"""
    time_slots = generate_time_slots()
    random.shuffle(time_slots)
    
    problem = Problem()
    
    # First, split subjects if needed
    all_subjects = []
    for subject in subjects:
        split_groups = split_subject_if_needed(subject, rooms)
        all_subjects.extend(split_groups)
    
    print(f"\nDEBUG: After splitting - Total subjects/groups: {len(all_subjects)}")
    
    # DEBUG: Print available resources
    print(f"DEBUG: Available Resources")
    print(f"Time slots: {len(time_slots)}")
    print(f"Rooms: {len(rooms)}")
    print(f"Subjects/Groups: {len(all_subjects)}")
    
    # Add variables with better domain filtering
    for subject in all_subjects:
        # Find suitable rooms for this subject/group
        suitable_rooms = [room['room_id'] for room in rooms 
                         if room['capacity'] >= subject['students']]
        
        if not suitable_rooms:
            # If no perfect fit, find the closest room
            closest_room = min(rooms, key=lambda r: abs(r['capacity'] - subject['students']))
            suitable_rooms = [closest_room['room_id']]
            print(f"Warning: No perfect room fit for {subject['subject_id']}. Using closest match: {closest_room['room_id']} (capacity: {closest_room['capacity']})")
        
        # Filter time slots based on constraints upfront
        available_slots = time_slots.copy()
        
        # Apply day off constraint
        if subject.get('day_off'):
            available_slots = [slot for slot in available_slots 
                             if slot.split('_')[0].lower() != subject['day_off'].lower()]
        
        # Apply time preference constraint
        if subject.get('time_preference') != 'any':
            available_slots = [slot for slot in available_slots 
                             if check_time_preference(slot, subject['time_preference'])]
        
        if not available_slots:
            print(f"Warning: No available time slots for {subject['subject_id']} after constraints")
            available_slots = time_slots  # Fallback to all slots
        
        problem.addVariable(f"{subject['subject_id']}_time", available_slots)
        problem.addVariable(f"{subject['subject_id']}_room", suitable_rooms)
        
        print(f"DEBUG: {subject['subject_id']} - {len(available_slots)} time slots, {len(suitable_rooms)} rooms")
    
    # CONSTRAINT 1: No professor double-booking
    professor_subjects = {}
    for subject in all_subjects:
        prof = subject['professor'].lower()
        if prof not in professor_subjects:
            professor_subjects[prof] = []
        professor_subjects[prof].append(subject['subject_id'])
    
    for prof, subject_ids in professor_subjects.items():
        if len(subject_ids) > 1:
            print(f"DEBUG: Professor {prof} teaches {len(subject_ids)} subjects/groups")
            for i in range(len(subject_ids)):
                for j in range(i + 1, len(subject_ids)):
                    subj1 = subject_ids[i]
                    subj2 = subject_ids[j]
                    problem.addConstraint(
                        lambda time1, time2: time1 != time2,
                        [f"{subj1}_time", f"{subj2}_time"]
                    )
    
    # CONSTRAINT 2: No room double-booking
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
    
    # CONSTRAINT 3: Room type constraints
    for subject in all_subjects:
        if subject.get('required_room_type'):
            required_type = subject['required_room_type'].lower()
            problem.addConstraint(
                lambda room_id, rt=required_type: 
                    any(room['room_type'].lower() == rt for room in rooms if room['room_id'] == room_id),
                [f"{subject['subject_id']}_room"]
            )
    
    # NEW CONSTRAINT 4: Split subject groups must be on same day and consecutive time slots
    grouped_subjects = {}
    for subject in all_subjects:
        if subject.get('is_split_group'):
            original_id = subject['original_subject_id']
            if original_id not in grouped_subjects:
                grouped_subjects[original_id] = []
            grouped_subjects[original_id].append(subject)
    
    for original_id, groups in grouped_subjects.items():
        if len(groups) > 1:
            print(f"DEBUG: Applying constraints for split subject {original_id} with {len(groups)} groups")
            
            # Groups must be on the same day
            group_ids = [group['subject_id'] for group in groups]
            for i in range(len(group_ids)):
                for j in range(i + 1, len(group_ids)):
                    subj1 = group_ids[i]
                    subj2 = group_ids[j]
                    problem.addConstraint(
                        lambda time1, time2: time1.split('_')[0] == time2.split('_')[0],
                        [f"{subj1}_time", f"{subj2}_time"]
                    )
            
            # Groups should have consecutive time slots (as much as possible)
            # This is a soft constraint - we'll try to encourage it but not require it
            if len(groups) == 2:
                # For 2 groups, try to make them consecutive
                subj1, subj2 = group_ids[0], group_ids[1]
                problem.addConstraint(
                    lambda time1, time2: are_time_slots_consecutive(time1, time2),
                    [f"{subj1}_time", f"{subj2}_time"]
                )
    
    return problem, time_slots, all_subjects  # Return modified subjects list

def are_time_slots_consecutive(slot1, slot2):
    """Check if two time slots are consecutive on the same day"""
    if slot1.split('_')[0] != slot2.split('_')[0]:
        return False  # Different days
    
    day = slot1.split('_')[0]
    time_part1 = slot1.split('_')[1]
    time_part2 = slot2.split('_')[1]
    
    # Get all time slots for this day
    all_slots = generate_time_slots()
    day_slots = [slot for slot in all_slots if slot.startswith(day)]
    day_slots.sort()
    
    try:
        idx1 = day_slots.index(slot1)
        idx2 = day_slots.index(slot2)
        return abs(idx1 - idx2) == 1
    except ValueError:
        return False

def create_fallback_scheduler(subjects, rooms):
    """Simplified scheduler with fewer constraints for when main scheduler fails"""
    time_slots = generate_time_slots()
    random.shuffle(time_slots)
    
    problem = Problem()
    
    print("\nTrying fallback scheduler with relaxed constraints...")
    
    # Split subjects if needed
    all_subjects = []
    for subject in subjects:
        split_groups = split_subject_if_needed(subject, rooms)
        all_subjects.extend(split_groups)
    
    # Only essential constraints
    for subject in all_subjects:
        # Very relaxed room filtering
        suitable_rooms = [room['room_id'] for room in rooms 
                         if room['capacity'] >= subject['students'] * 0.5]
        
        if not suitable_rooms:
            suitable_rooms = [room['room_id'] for room in rooms]
        
        problem.addVariable(f"{subject['subject_id']}_time", time_slots)
        problem.addVariable(f"{subject['subject_id']}_room", suitable_rooms)
    
    # Only essential constraint: no room double-booking
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

def print_schedule(solution, subjects, time_slots):
    """Print the generated schedule with grouping information"""
    if not solution:
        print("No solution found!")
        return
    
    print("\n" + "="*80)
    print("GENERATED SCHEDULE")
    print("="*80)
    
    # Group by original subject for split groups
    original_subjects = {}
    for subject in subjects:
        original_id = subject.get('original_subject_id', subject['subject_id'])
        if original_id not in original_subjects:
            original_subjects[original_id] = {
                'original_name': subject['subject_name'],
                'professor': subject['professor'],
                'total_students': 0,
                'groups': []
            }
        original_subjects[original_id]['groups'].append(subject)
        if 'is_split_group' not in subject:
            original_subjects[original_id]['total_students'] = subject['students']
        else:
            original_subjects[original_id]['total_students'] += subject['students']
    
    # Display split subject information
    split_subjects = {k: v for k, v in original_subjects.items() if len(v['groups']) > 1}
    if split_subjects:
        print("\nSPLIT SUBJECTS (Large classes divided into groups):")
        for original_id, info in split_subjects.items():
            print(f"  {original_id}: {info['original_name']} - {info['total_students']} students split into {len(info['groups'])} groups")
    
    # Group by day for better organization
    schedule_by_day = {}
    for key, value in solution.items():
        if key.endswith('_time'):
            subject_id = key.replace('_time', '')
            room_key = f"{subject_id}_room"
            room = solution[room_key]
            day = value.split('_')[0]
            
            if day not in schedule_by_day:
                schedule_by_day[day] = []
            
            subject_info = next(s for s in subjects if s['subject_id'] == subject_id)
            schedule_by_day[day].append({
                'time_slot': value,
                'subject': subject_info,
                'room': room,
                'duration': get_slot_duration(value)
            })
    
    # Print schedule organized by day
    for day in sorted(schedule_by_day.keys()):
        print(f"\n{day.upper()}:")
        print("-" * 60)
        
        # Sort by time
        day_schedule = sorted(schedule_by_day[day], key=lambda x: x['time_slot'])
        
        for entry in day_schedule:
            subject = entry['subject']
            prof = subject['professor']
            is_split = subject.get('is_split_group', False)
            original_id = subject.get('original_subject_id', subject['subject_id'])
            
            display_prof = f"Dr. {prof}" if not prof.lower().startswith('dr.') else prof
            time_part = entry['time_slot'].split('_')[1]
            
            group_info = ""
            if is_split:
                group_info = f" [Group {subject['group_number']}/{subject['total_groups']}]"
            
            print(f"  {time_part:<11} | Room: {entry['room']:<6} | {display_prof:<15} | {subject['subject_name']}{group_info}")

def get_slot_duration(slot):
    day, time_range = slot.split('_')
    start, end = time_range.split('-')
    start_h, start_m = map(int, start.split(':')) if ':' in start else (int(start), 0)
    end_h, end_m = map(int, end.split(':')) if ':' in end else (int(end), 0)
    duration = (end_h + end_m/60) - (start_h + start_m/60)
    return duration

def get_available_days(time_slots):
    return list(set(slot.split('_')[0] for slot in time_slots))

def generate_time_slots(days=['Sun', 'Mon', 'Tue', 'Wed', 'Thu']):
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
    hours = int(hour_float)
    minutes = int((hour_float - hours) * 60)
    return f"{hours}:{minutes:02d}"

def validate_constraints(solution, subjects):
    """Validate constraints including split subject constraints"""
    day_off_violations = []
    time_pref_violations = []
    split_group_violations = []
    
    # Check for split subject constraints
    grouped_subjects = {}
    for subject in subjects:
        if subject.get('is_split_group'):
            original_id = subject['original_subject_id']
            if original_id not in grouped_subjects:
                grouped_subjects[original_id] = []
            grouped_subjects[original_id].append(subject)
    
    for original_id, groups in grouped_subjects.items():
        if len(groups) > 1:
            # Check if all groups are on same day
            group_times = []
            for group in groups:
                group_id = group['subject_id']
                if f"{group_id}_time" in solution:
                    group_times.append(solution[f"{group_id}_time"])
            
            days = [time.split('_')[0] for time in group_times]
            if len(set(days)) > 1:
                split_group_violations.append(f"❌ Split subject {original_id} groups are on different days")
            
            # Check if groups have consecutive time slots
            if len(groups) == 2:
                time1, time2 = group_times[0], group_times[1]
                if not are_time_slots_consecutive(time1, time2):
                    split_group_violations.append(f"⚠️ Split subject {original_id} groups are not in consecutive time slots")
    
    for key, time_slot in solution.items():
        if key.endswith('_time'):
            subject_id = key.replace('_time', '')
            subject = next(s for s in subjects if s['subject_id'] == subject_id)
            professor = subject['professor']
            day_off = subject.get('day_off')
            time_pref = subject.get('time_preference', 'any')
            day = time_slot.split('_')[0]
            
            if day_off and day_off.lower() == day.lower():
                day_off_violations.append(f"❌ {professor} scheduled on {day} (day off) for {subject['subject_name']}")
            
            if time_pref != 'any' and not check_time_preference(time_slot, time_pref):
                time_pref_violations.append(f"❌ {professor}'s time preference ({time_pref}) violated for {subject['subject_name']} at {time_slot}")
    
    print("\n" + "="*70)
    print("VALIDATION REPORT:")
    print("="*70)
    
    if day_off_violations:
        print("DAY OFF CONSTRAINT VIOLATIONS:")
        for violation in day_off_violations:
            print(f"  {violation}")
    else:
        print("✅ All day off constraints satisfied!")
    
    if time_pref_violations:
        print("\nTIME PREFERENCE CONSTRAINT VIOLATIONS:")
        for violation in time_pref_violations:
            print(f"  {violation}")
    else:
        print("✅ All time preference constraints satisfied!")
    
    if split_group_violations:
        print("\nSPLIT GROUP CONSTRAINT VIOLATIONS:")
        for violation in split_group_violations:
            print(f"  {violation}")
    else:
        print("✅ All split group constraints satisfied!")

def main():
    print("=== University Schedule Generator ===")
    print("Now with Room Capacity Splitting for Large Classes!")
    print("="*60)
    
    # Get all data from user
    subjects, rooms = get_user_input()
    
    # Display input summary
    print("\n" + "="*60)
    print("INPUT SUMMARY:")
    print("="*60)
    print(f"Subjects: {len(subjects)}")
    for subject in subjects:
        day_off_info = f" | Day off: {subject['day_off']}" if subject.get('day_off') else ""
        pref_info = f" | Time preference: {subject['time_preference']}" if subject.get('time_preference') != 'any' else ""
        print(f"  - {subject['subject_id']}: {subject['subject_name']} by {subject['professor']} ({subject['students']} students){day_off_info}{pref_info}")
    
    print(f"\nRooms: {len(rooms)}")
    for room in rooms:
        print(f"  - {room['room_id']}: {room['capacity']} seats ({room['room_type']})")
    
    # Check if any subjects need splitting
    max_capacity = max(room['capacity'] for room in rooms) if rooms else 0
    large_subjects = [s for s in subjects if s['students'] > max_capacity]
    if large_subjects:
        print(f"\nNOTE: {len(large_subjects)} subject(s) will be split into multiple groups due to room capacity limits")
        for subject in large_subjects:
            groups_needed = math.ceil(subject['students'] / max_capacity)
            print(f"  - {subject['subject_id']}: {subject['students']} students → {groups_needed} groups")
    
    # Try main scheduler first
    problem, time_slots, all_subjects = create_basic_scheduler(subjects, rooms)
    
    print(f"\nScheduling Information:")
    print(f"  Time slots generated: {len(time_slots)}")
    print(f"  Available days: {', '.join(sorted(get_available_days(time_slots)))}")
    print(f"  Total subjects/groups to schedule: {len(all_subjects)}")
    
    print("\n" + "="*60)
    print("ATTEMPTING TO GENERATE SCHEDULE...")
    print("="*60)
    
    solution = None
    max_attempts = 3
    
    for attempt in range(max_attempts):
        print(f"\nAttempt {attempt + 1}/{max_attempts}...")
        
        if attempt == 0:
            # First attempt: full constraints
            problem, time_slots, all_subjects = create_basic_scheduler(subjects, rooms)
        else:
            # Subsequent attempts: relaxed constraints
            problem, time_slots, all_subjects = create_fallback_scheduler(subjects, rooms)
        
        solution = problem.getSolution()
        
        if solution:
            print(f"✅ Solution found on attempt {attempt + 1}!")
            break
        else:
            print(f"❌ No solution found with current constraint level")
    
    if solution:
        print_schedule(solution, all_subjects, time_slots)
        validate_constraints(solution, all_subjects)
        
        # Statistics
        total_hours = sum(get_slot_duration(slot) for slot in solution.values() 
                         if isinstance(slot, str) and '_' in slot)
        utilized_slots = len(set(solution.values()))
        
        print(f"\nSchedule Statistics:")
        print(f"  Total instructional hours: {total_hours}")
        print(f"  Subjects/groups scheduled: {len(all_subjects)}")
        print(f"  Time slots utilized: {utilized_slots}/{len(time_slots)}")
        print(f"  Room utilization: {utilized_slots/len(rooms)*100:.1f}%")
        
    else:
        print("\n❌ No feasible schedule found after all attempts!")
        print("\nDetailed Analysis:")
        print(f"- Total time slots available: {len(time_slots)}")
        print(f"- Rooms available: {len(rooms)}")
        print(f"- Subjects/groups to schedule: {len(all_subjects)}")
        
        if len(time_slots) < len(all_subjects):
            print("❌ Problem: Not enough time slots for all subjects/groups!")
        
        # Suggest solutions
        print("\nSuggested Solutions:")
        print("1. Add more rooms or increase room capacities")
        print("2. Reduce the number of constraints (day offs, time preferences)")
        print("3. Add more available days or time slots")
        print("ali")

if __name__ == "__main__":
    main()