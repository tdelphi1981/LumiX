"""Interactive HTML Report Generator for Timetabling Solutions.

This module generates a modern, interactive HTML5 + CSS dashboard for visualizing
timetabling optimization results with multiple perspectives and rich analytics.

Features:
    - Summary dashboard with statistics and goal satisfaction metrics
    - Teacher timetables with weekly grid views
    - Class timetables showing student schedules
    - Room timetables with utilization rates
    - Color-coded subjects with consistent palette
    - Room type badges (REGULAR/LAB/GYM)
    - Interactive navigation and filtering
    - Responsive design for different screen sizes
    - Self-contained single HTML file (no external dependencies)

Usage:
    >>> from report_generator import generate_html_report
    >>> generate_html_report(solution, session, "timetable_report.html")
"""

import json
from typing import Dict, List, Tuple, Any
from database import (
    Teacher,
    Classroom,
    SchoolClass,
    Subject,
    Lecture,
    TimeSlot,
    TeacherPreference,
    get_teacher_name,
    get_subject_name,
    get_class_name,
    get_classroom_name,
    calculate_priority_from_work_years,
)


def extract_schedule_data(solution, session) -> Dict[Tuple[int, int, int], int]:
    """Extract schedule assignments from solution.

    Args:
        solution: LXSolution object
        session: SQLAlchemy Session

    Returns:
        Dictionary mapping (lecture_id, timeslot_id, classroom_id) to 1 if assigned
    """
    schedule_data = {}
    for (lecture_id, timeslot_id, classroom_id), value in solution.variables["assignment"].items():
        if value > 0.5:  # Binary variable is 1
            schedule_data[(lecture_id, timeslot_id, classroom_id)] = 1
    return schedule_data


def calculate_statistics(solution, session, schedule_data: Dict) -> Dict[str, Any]:
    """Calculate summary statistics for the dashboard.

    Args:
        solution: LXSolution object
        session: SQLAlchemy Session
        schedule_data: Extracted schedule assignments

    Returns:
        Dictionary containing various statistics
    """
    teachers = session.query(Teacher).all()
    classrooms = session.query(Classroom).all()
    classes = session.query(SchoolClass).all()
    lectures = session.query(Lecture).all()
    timeslots = session.query(TimeSlot).all()
    preferences = session.query(TeacherPreference).all()

    # Room type usage
    room_usage = {"REGULAR": 0, "LAB": 0, "GYM": 0}
    for (lecture_id, timeslot_id, classroom_id), value in schedule_data.items():
        classroom = session.query(Classroom).filter_by(id=classroom_id).first()
        if classroom:
            room_usage[classroom.room_type] += 1

    # Room utilization percentage
    total_slots = len(timeslots)
    room_utilization = {}
    for classroom in classrooms:
        used_slots = sum(1 for (lid, tid, cid) in schedule_data.keys() if cid == classroom.id)
        utilization = (used_slots / total_slots * 100) if total_slots > 0 else 0
        room_utilization[classroom.id] = utilization

    # Goal satisfaction by priority
    goal_satisfaction = {1: {"satisfied": 0, "total": 0},
                        2: {"satisfied": 0, "total": 0},
                        3: {"satisfied": 0, "total": 0}}

    for pref in preferences:
        teacher = session.query(Teacher).filter_by(id=pref.teacher_id).first()
        if not teacher:
            continue

        priority = calculate_priority_from_work_years(teacher.work_years)
        goal_satisfaction[priority]["total"] += 1

        # Check if goal was satisfied
        constraint_name = None
        if pref.preference_type == "DAY_OFF":
            constraint_name = f"pref_{pref.id}_day_off"
        elif pref.preference_type == "SPECIFIC_TIME":
            constraint_name = f"pref_{pref.id}_specific_time"

        if constraint_name:
            try:
                deviations = solution.get_goal_deviations(constraint_name)

                # Extract deviation value from nested structure
                if isinstance(deviations, dict):
                    pos_dict = deviations.get("pos", {})
                    neg_dict = deviations.get("neg", {})

                    if isinstance(pos_dict, dict):
                        pos_value = sum(v for v in pos_dict.values() if isinstance(v, (int, float)))
                    else:
                        pos_value = pos_dict if isinstance(pos_dict, (int, float)) else 0

                    if isinstance(neg_dict, dict):
                        neg_value = sum(v for v in neg_dict.values() if isinstance(v, (int, float)))
                    else:
                        neg_value = neg_dict if isinstance(neg_dict, (int, float)) else 0

                    dev_value = pos_value + neg_value
                else:
                    dev_value = deviations if isinstance(deviations, (int, float)) else 0

                if dev_value < 0.1:
                    goal_satisfaction[priority]["satisfied"] += 1
            except:
                # If we can't get deviations, assume not satisfied
                pass

    # Teacher workload distribution
    teacher_workload = {}
    for teacher in teachers:
        teacher_lectures = sum(1 for (lid, tid, cid) in schedule_data.keys()
                              if any(lec.id == lid and lec.teacher_id == teacher.id
                                    for lec in lectures))
        teacher_workload[teacher.id] = teacher_lectures

    return {
        "total_teachers": len(teachers),
        "total_classrooms": len(classrooms),
        "total_classes": len(classes),
        "total_lectures": len(lectures),
        "lectures_scheduled": len(schedule_data),
        "total_timeslots": len(timeslots),
        "room_usage": room_usage,
        "room_utilization": room_utilization,
        "goal_satisfaction": goal_satisfaction,
        "teacher_workload": teacher_workload,
        "solution_status": solution.status,
    }


def generate_subject_colors() -> Dict[str, str]:
    """Generate consistent color palette for subjects.

    Returns:
        Dictionary mapping subject names to hex color codes
    """
    return {
        "Mathematics": "#3498db",
        "English": "#e74c3c",
        "Physics": "#9b59b6",
        "Chemistry": "#1abc9c",
        "Biology": "#27ae60",
        "History": "#f39c12",
        "Geography": "#16a085",
        "Physical Education": "#e67e22",
        "Computer Science": "#34495e",
        "Art": "#e91e63",
        "Music": "#9c27b0",
        "Foreign Language": "#00bcd4",
    }


def generate_teacher_timetable_html(teacher: Teacher, schedule_data: Dict, session) -> str:
    """Generate HTML for a single teacher's timetable.

    Args:
        teacher: Teacher object
        schedule_data: Schedule assignments
        session: SQLAlchemy Session

    Returns:
        HTML string for the teacher's timetable
    """
    lectures = session.query(Lecture).filter_by(teacher_id=teacher.id).all()
    timeslots = session.query(TimeSlot).all()
    classrooms = session.query(Classroom).all()
    subject_colors = generate_subject_colors()

    # Create 8x5 grid (8 periods, 5 days)
    grid = [[None for _ in range(5)] for _ in range(8)]

    # Fill grid
    for lecture in lectures:
        for timeslot in timeslots:
            for classroom in classrooms:
                key = (lecture.id, timeslot.id, classroom.id)
                if schedule_data.get(key, 0) == 1:
                    subject = session.query(Subject).filter_by(id=lecture.subject_id).first()
                    school_class = session.query(SchoolClass).filter_by(id=lecture.class_id).first()

                    subject_name = subject.name if subject else "Unknown"
                    class_name = school_class.name if school_class else "Unknown"
                    room_name = classroom.name
                    room_type = classroom.room_type

                    color = subject_colors.get(subject_name, "#95a5a6")

                    grid[timeslot.period - 1][timeslot.day_of_week] = {
                        "subject": subject_name,
                        "class": class_name,
                        "room": room_name,
                        "room_type": room_type,
                        "color": color
                    }

    # Generate HTML
    html = f"""
    <div class="timetable-card">
        <h3>{teacher.name} <span class="badge">({teacher.work_years} years)</span></h3>
        <table class="timetable">
            <thead>
                <tr>
                    <th>Period</th>
                    <th>Monday</th>
                    <th>Tuesday</th>
                    <th>Wednesday</th>
                    <th>Thursday</th>
                    <th>Friday</th>
                </tr>
            </thead>
            <tbody>
    """

    for period in range(8):
        html += f"<tr><td class='period-label'>{period + 1}</td>"
        for day in range(5):
            cell = grid[period][day]
            if cell:
                html += f"""
                <td class="lecture-cell" style="border-left: 4px solid {cell['color']}">
                    <div class="lecture-subject">{cell['subject']}</div>
                    <div class="lecture-details">{cell['class']}</div>
                    <div class="lecture-room">
                        <span class="room-badge room-{cell['room_type'].lower()}">{cell['room_type'][0]}</span>
                        {cell['room']}
                    </div>
                </td>
                """
            else:
                html += '<td class="empty-cell">—</td>'
        html += "</tr>"

    html += """
            </tbody>
        </table>
    </div>
    """

    return html


def generate_class_timetable_html(school_class: SchoolClass, schedule_data: Dict, session) -> str:
    """Generate HTML for a single class's timetable.

    Args:
        school_class: SchoolClass object
        schedule_data: Schedule assignments
        session: SQLAlchemy Session

    Returns:
        HTML string for the class's timetable
    """
    lectures = session.query(Lecture).filter_by(class_id=school_class.id).all()
    timeslots = session.query(TimeSlot).all()
    classrooms = session.query(Classroom).all()
    subject_colors = generate_subject_colors()

    # Create 8x5 grid
    grid = [[None for _ in range(5)] for _ in range(8)]

    # Fill grid
    for lecture in lectures:
        for timeslot in timeslots:
            for classroom in classrooms:
                key = (lecture.id, timeslot.id, classroom.id)
                if schedule_data.get(key, 0) == 1:
                    subject = session.query(Subject).filter_by(id=lecture.subject_id).first()
                    teacher = session.query(Teacher).filter_by(id=lecture.teacher_id).first()

                    subject_name = subject.name if subject else "Unknown"
                    teacher_name = teacher.name if teacher else "Unknown"
                    room_name = classroom.name
                    room_type = classroom.room_type

                    color = subject_colors.get(subject_name, "#95a5a6")

                    grid[timeslot.period - 1][timeslot.day_of_week] = {
                        "subject": subject_name,
                        "teacher": teacher_name,
                        "room": room_name,
                        "room_type": room_type,
                        "color": color
                    }

    # Generate HTML
    html = f"""
    <div class="timetable-card">
        <h3>Class {school_class.name} <span class="badge">({school_class.size} students)</span></h3>
        <table class="timetable">
            <thead>
                <tr>
                    <th>Period</th>
                    <th>Monday</th>
                    <th>Tuesday</th>
                    <th>Wednesday</th>
                    <th>Thursday</th>
                    <th>Friday</th>
                </tr>
            </thead>
            <tbody>
    """

    for period in range(8):
        html += f"<tr><td class='period-label'>{period + 1}</td>"
        for day in range(5):
            cell = grid[period][day]
            if cell:
                html += f"""
                <td class="lecture-cell" style="border-left: 4px solid {cell['color']}">
                    <div class="lecture-subject">{cell['subject']}</div>
                    <div class="lecture-details">{cell['teacher']}</div>
                    <div class="lecture-room">
                        <span class="room-badge room-{cell['room_type'].lower()}">{cell['room_type'][0]}</span>
                        {cell['room']}
                    </div>
                </td>
                """
            else:
                html += '<td class="empty-cell">—</td>'
        html += "</tr>"

    html += """
            </tbody>
        </table>
    </div>
    """

    return html


def generate_room_timetable_html(classroom: Classroom, schedule_data: Dict, session, utilization: float) -> str:
    """Generate HTML for a single room's timetable.

    Args:
        classroom: Classroom object
        schedule_data: Schedule assignments
        session: SQLAlchemy Session
        utilization: Room utilization percentage

    Returns:
        HTML string for the room's timetable
    """
    lectures = session.query(Lecture).all()
    timeslots = session.query(TimeSlot).all()
    subject_colors = generate_subject_colors()

    # Create 8x5 grid
    grid = [[None for _ in range(5)] for _ in range(8)]

    # Fill grid
    for lecture in lectures:
        for timeslot in timeslots:
            key = (lecture.id, timeslot.id, classroom.id)
            if schedule_data.get(key, 0) == 1:
                subject = session.query(Subject).filter_by(id=lecture.subject_id).first()
                teacher = session.query(Teacher).filter_by(id=lecture.teacher_id).first()
                school_class = session.query(SchoolClass).filter_by(id=lecture.class_id).first()

                subject_name = subject.name if subject else "Unknown"
                teacher_name = teacher.name if teacher else "Unknown"
                class_name = school_class.name if school_class else "Unknown"

                color = subject_colors.get(subject_name, "#95a5a6")

                grid[timeslot.period - 1][timeslot.day_of_week] = {
                    "subject": subject_name,
                    "teacher": teacher_name,
                    "class": class_name,
                    "color": color
                }

    # Generate HTML
    html = f"""
    <div class="timetable-card">
        <h3>{classroom.name}
            <span class="room-badge room-{classroom.room_type.lower()}">{classroom.room_type}</span>
            <span class="badge">Capacity: {classroom.capacity}</span>
            <span class="badge">Utilization: {utilization:.1f}%</span>
        </h3>
        <table class="timetable">
            <thead>
                <tr>
                    <th>Period</th>
                    <th>Monday</th>
                    <th>Tuesday</th>
                    <th>Wednesday</th>
                    <th>Thursday</th>
                    <th>Friday</th>
                </tr>
            </thead>
            <tbody>
    """

    for period in range(8):
        html += f"<tr><td class='period-label'>{period + 1}</td>"
        for day in range(5):
            cell = grid[period][day]
            if cell:
                html += f"""
                <td class="lecture-cell" style="border-left: 4px solid {cell['color']}">
                    <div class="lecture-subject">{cell['subject']}</div>
                    <div class="lecture-details">{cell['teacher']}</div>
                    <div class="lecture-room">{cell['class']}</div>
                </td>
                """
            else:
                html += '<td class="empty-cell">—</td>'
        html += "</tr>"

    html += """
            </tbody>
        </table>
    </div>
    """

    return html


def generate_html_report(solution, session, output_path: str = "timetable_report.html"):
    """Generate comprehensive interactive HTML report for timetabling solution.

    Creates a modern, self-contained HTML5 + CSS dashboard with multiple views:
    - Summary dashboard with statistics and charts
    - Teacher timetables
    - Class timetables
    - Room timetables

    Args:
        solution: LXSolution object from optimization
        session: SQLAlchemy Session for database access
        output_path: Path where HTML file will be saved

    Example:
        >>> from report_generator import generate_html_report
        >>> generate_html_report(solution, session, "report.html")
        HTML report generated: report.html
    """
    if not solution.is_optimal() and not solution.is_feasible():
        print("\n❌ No feasible solution to generate report from!")
        return

    print("\n" + "=" * 80)
    print("GENERATING INTERACTIVE HTML REPORT")
    print("=" * 80)

    # Extract data
    schedule_data = extract_schedule_data(solution, session)
    stats = calculate_statistics(solution, session, schedule_data)

    teachers = session.query(Teacher).all()
    classes = session.query(SchoolClass).all()
    classrooms = session.query(Classroom).all()

    print(f"  Processing {len(teachers)} teachers...")
    print(f"  Processing {len(classes)} classes...")
    print(f"  Processing {len(classrooms)} rooms...")

    # Generate timetables HTML
    teacher_timetables = ""
    for teacher in sorted(teachers, key=lambda t: t.name):
        teacher_timetables += generate_teacher_timetable_html(teacher, schedule_data, session)

    class_timetables = ""
    for school_class in sorted(classes, key=lambda c: c.name):
        class_timetables += generate_class_timetable_html(school_class, schedule_data, session)

    room_timetables = ""
    for classroom in sorted(classrooms, key=lambda r: r.name):
        utilization = stats["room_utilization"].get(classroom.id, 0)
        room_timetables += generate_room_timetable_html(classroom, schedule_data, session, utilization)

    # Generate summary dashboard HTML
    goal_p1_pct = (stats["goal_satisfaction"][1]["satisfied"] / stats["goal_satisfaction"][1]["total"] * 100) if stats["goal_satisfaction"][1]["total"] > 0 else 0
    goal_p2_pct = (stats["goal_satisfaction"][2]["satisfied"] / stats["goal_satisfaction"][2]["total"] * 100) if stats["goal_satisfaction"][2]["total"] > 0 else 0
    goal_p3_pct = (stats["goal_satisfaction"][3]["satisfied"] / stats["goal_satisfaction"][3]["total"] * 100) if stats["goal_satisfaction"][3]["total"] > 0 else 0

    summary_html = f"""
    <div class="dashboard-grid">
        <div class="stat-card">
            <h3>Lectures Scheduled</h3>
            <div class="stat-value">{stats['lectures_scheduled']}/{stats['total_lectures']}</div>
            <div class="stat-label">Total Coverage</div>
        </div>
        <div class="stat-card">
            <h3>Teachers</h3>
            <div class="stat-value">{stats['total_teachers']}</div>
            <div class="stat-label">Instructors</div>
        </div>
        <div class="stat-card">
            <h3>Classes</h3>
            <div class="stat-value">{stats['total_classes']}</div>
            <div class="stat-label">Student Groups</div>
        </div>
        <div class="stat-card">
            <h3>Classrooms</h3>
            <div class="stat-value">{stats['total_classrooms']}</div>
            <div class="stat-label">Available Rooms</div>
        </div>
    </div>

    <div class="dashboard-section">
        <h2>Room Usage by Type</h2>
        <div class="room-usage-grid">
            <div class="usage-card">
                <span class="room-badge room-regular">R</span>
                <span class="usage-label">Regular Classrooms</span>
                <span class="usage-value">{stats['room_usage']['REGULAR']} assignments</span>
            </div>
            <div class="usage-card">
                <span class="room-badge room-lab">L</span>
                <span class="usage-label">Laboratory Rooms</span>
                <span class="usage-value">{stats['room_usage']['LAB']} assignments</span>
            </div>
            <div class="usage-card">
                <span class="room-badge room-gym">G</span>
                <span class="usage-label">Gymnasium</span>
                <span class="usage-value">{stats['room_usage']['GYM']} assignments</span>
            </div>
        </div>
    </div>

    <div class="dashboard-section">
        <h2>Goal Satisfaction by Priority</h2>
        <div class="goal-satisfaction">
            <div class="goal-item">
                <div class="goal-header">
                    <span class="goal-label">Priority 1 (Senior Teachers)</span>
                    <span class="goal-value">{stats['goal_satisfaction'][1]['satisfied']}/{stats['goal_satisfaction'][1]['total']} ({goal_p1_pct:.0f}%)</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {goal_p1_pct}%"></div>
                </div>
            </div>
            <div class="goal-item">
                <div class="goal-header">
                    <span class="goal-label">Priority 2 (Mid-Level Teachers)</span>
                    <span class="goal-value">{stats['goal_satisfaction'][2]['satisfied']}/{stats['goal_satisfaction'][2]['total']} ({goal_p2_pct:.0f}%)</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {goal_p2_pct}%"></div>
                </div>
            </div>
            <div class="goal-item">
                <div class="goal-header">
                    <span class="goal-label">Priority 3 (Junior Teachers)</span>
                    <span class="goal-value">{stats['goal_satisfaction'][3]['satisfied']}/{stats['goal_satisfaction'][3]['total']} ({goal_p3_pct:.0f}%)</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {goal_p3_pct}%"></div>
                </div>
            </div>
        </div>
    </div>
    """

    # Complete HTML document
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Timetable Report - High School Course Scheduling</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            padding: 20px;
            min-height: 100vh;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}

        header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}

        header h1 {{
            font-size: 2.5rem;
            margin-bottom: 10px;
        }}

        header p {{
            font-size: 1.1rem;
            opacity: 0.9;
        }}

        .tabs {{
            display: flex;
            background: #f8f9fa;
            border-bottom: 2px solid #dee2e6;
            overflow-x: auto;
        }}

        .tab {{
            padding: 18px 30px;
            cursor: pointer;
            border: none;
            background: none;
            font-size: 1rem;
            font-weight: 600;
            color: #6c757d;
            transition: all 0.3s ease;
            white-space: nowrap;
        }}

        .tab:hover {{
            background: rgba(102, 126, 234, 0.1);
            color: #667eea;
        }}

        .tab.active {{
            color: #667eea;
            border-bottom: 3px solid #667eea;
            background: white;
        }}

        .tab-content {{
            display: none;
            padding: 30px;
            animation: fadeIn 0.3s ease;
        }}

        .tab-content.active {{
            display: block;
        }}

        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(10px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        .dashboard-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}

        .stat-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }}

        .stat-card h3 {{
            font-size: 0.9rem;
            opacity: 0.9;
            margin-bottom: 10px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}

        .stat-value {{
            font-size: 2.5rem;
            font-weight: 700;
            margin: 10px 0;
        }}

        .stat-label {{
            font-size: 0.9rem;
            opacity: 0.8;
        }}

        .dashboard-section {{
            margin: 30px 0;
            padding: 25px;
            background: #f8f9fa;
            border-radius: 12px;
        }}

        .dashboard-section h2 {{
            color: #667eea;
            margin-bottom: 20px;
            font-size: 1.5rem;
        }}

        .room-usage-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
        }}

        .usage-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            display: flex;
            flex-direction: column;
            align-items: center;
            text-align: center;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}

        .usage-label {{
            margin: 10px 0 5px 0;
            font-weight: 600;
            color: #495057;
        }}

        .usage-value {{
            font-size: 1.2rem;
            color: #667eea;
            font-weight: 700;
        }}

        .goal-satisfaction {{
            display: flex;
            flex-direction: column;
            gap: 20px;
        }}

        .goal-item {{
            background: white;
            padding: 20px;
            border-radius: 8px;
        }}

        .goal-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }}

        .goal-label {{
            font-weight: 600;
            color: #495057;
        }}

        .goal-value {{
            font-weight: 700;
            color: #667eea;
        }}

        .progress-bar {{
            width: 100%;
            height: 12px;
            background: #e9ecef;
            border-radius: 6px;
            overflow: hidden;
        }}

        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            transition: width 0.5s ease;
        }}

        .timetable-card {{
            margin-bottom: 40px;
            background: #f8f9fa;
            padding: 25px;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }}

        .timetable-card h3 {{
            color: #667eea;
            margin-bottom: 20px;
            font-size: 1.3rem;
            display: flex;
            align-items: center;
            gap: 10px;
            flex-wrap: wrap;
        }}

        .badge {{
            background: #e9ecef;
            color: #495057;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 600;
        }}

        .room-badge {{
            display: inline-block;
            width: 28px;
            height: 28px;
            line-height: 28px;
            text-align: center;
            border-radius: 50%;
            font-weight: 700;
            font-size: 0.8rem;
            color: white;
        }}

        .room-regular {{
            background: #3498db;
        }}

        .room-lab {{
            background: #1abc9c;
        }}

        .room-gym {{
            background: #e67e22;
        }}

        .timetable {{
            width: 100%;
            border-collapse: collapse;
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }}

        .timetable th {{
            background: #667eea;
            color: white;
            padding: 15px 10px;
            text-align: center;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            font-size: 0.85rem;
        }}

        .timetable td {{
            padding: 12px 10px;
            text-align: center;
            border: 1px solid #dee2e6;
            vertical-align: middle;
        }}

        .period-label {{
            background: #f8f9fa;
            font-weight: 700;
            color: #667eea;
            font-size: 1rem;
        }}

        .lecture-cell {{
            background: white;
            text-align: left;
            transition: all 0.2s ease;
            cursor: default;
        }}

        .lecture-cell:hover {{
            transform: scale(1.02);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            z-index: 10;
        }}

        .lecture-subject {{
            font-weight: 700;
            font-size: 0.95rem;
            margin-bottom: 5px;
            color: #2c3e50;
        }}

        .lecture-details {{
            font-size: 0.85rem;
            color: #6c757d;
            margin-bottom: 5px;
        }}

        .lecture-room {{
            font-size: 0.8rem;
            color: #495057;
            display: flex;
            align-items: center;
            gap: 5px;
        }}

        .empty-cell {{
            background: #f8f9fa;
            color: #adb5bd;
            font-weight: 300;
            font-size: 1.2rem;
        }}

        @media (max-width: 768px) {{
            body {{
                padding: 10px;
            }}

            header h1 {{
                font-size: 1.8rem;
            }}

            .tab {{
                padding: 12px 20px;
                font-size: 0.9rem;
            }}

            .tab-content {{
                padding: 15px;
            }}

            .timetable {{
                font-size: 0.8rem;
            }}

            .timetable th, .timetable td {{
                padding: 8px 5px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>High School Course Timetable</h1>
            <p>Interactive Scheduling Report - Generated by LumiX Optimization</p>
        </header>

        <div class="tabs">
            <button class="tab active" onclick="showTab('summary')">Summary Dashboard</button>
            <button class="tab" onclick="showTab('teachers')">Teacher Timetables</button>
            <button class="tab" onclick="showTab('classes')">Class Timetables</button>
            <button class="tab" onclick="showTab('rooms')">Room Timetables</button>
        </div>

        <div id="summary" class="tab-content active">
            <h2>Summary Dashboard</h2>
            {summary_html}
        </div>

        <div id="teachers" class="tab-content">
            <h2>Teacher Timetables</h2>
            <p style="margin-bottom: 20px; color: #6c757d;">Weekly schedules for all teachers</p>
            {teacher_timetables}
        </div>

        <div id="classes" class="tab-content">
            <h2>Class Timetables</h2>
            <p style="margin-bottom: 20px; color: #6c757d;">Weekly schedules for all student classes</p>
            {class_timetables}
        </div>

        <div id="rooms" class="tab-content">
            <h2>Room Timetables</h2>
            <p style="margin-bottom: 20px; color: #6c757d;">Weekly room utilization schedules</p>
            {room_timetables}
        </div>
    </div>

    <script>
        function showTab(tabName) {{
            // Hide all tab contents
            const contents = document.querySelectorAll('.tab-content');
            contents.forEach(content => content.classList.remove('active'));

            // Deactivate all tabs
            const tabs = document.querySelectorAll('.tab');
            tabs.forEach(tab => tab.classList.remove('active'));

            // Show selected tab content
            document.getElementById(tabName).classList.add('active');

            // Activate selected tab
            event.target.classList.add('active');
        }}
    </script>
</body>
</html>"""

    # Write to file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"\n  ✓ HTML report generated: {output_path}")
    print(f"  ✓ Includes {len(teachers)} teacher timetables")
    print(f"  ✓ Includes {len(classes)} class timetables")
    print(f"  ✓ Includes {len(classrooms)} room timetables")
    print("=" * 80)
