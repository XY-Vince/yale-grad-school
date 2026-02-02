"""
Web Interface for GradQuest.

A Flask-based browser interface for playing the game.
"""

from __future__ import annotations
from flask import Flask, render_template, jsonify, request, session
from pathlib import Path
import secrets
import json

from gradquest.core.game_engine import GameEngine, EndGameState

app = Flask(__name__, 
            template_folder='templates',
            static_folder='static')
app.secret_key = secrets.token_hex(16)

# Store game engines per session
game_engines = {}


def get_engine():
    """Get or create game engine for current session."""
    session_id = session.get('session_id')
    if not session_id or session_id not in game_engines:
        session_id = secrets.token_hex(8)
        session['session_id'] = session_id
        
        # Create new engine
        data_path = Path(__file__).parent.parent / 'data' / 'rulesets' / 'default'
        engine = GameEngine(data_path)
        engine.load_game_data()
        game_engines[session_id] = engine
    
    return game_engines[session_id]


def get_game_state(engine):
    """Get current game state as dict."""
    stats = engine.get_stats()
    vs = engine.variable_store
    
    # Get items
    items = []
    for item_id, count in vs.get_all_items().items():
        items.append({
            'id': item_id,
            'name': item_id.replace('_', ' ').title(),
            'count': count
        })
    
    # Get status effects with descriptions
    statuses = []
    status_descriptions = {
        'exhaustion': 'Drains 5 morale/month',
        'unhappyAdvisor': 'Drains 5 morale/month', 
        'brokenEquipment': 'Cannot work on figures',
        'firstYear': 'Bonus morale regen'
    }
    status_display_names = {
        'exhaustion': 'Exhaustion',
        'unhappyAdvisor': 'Unhappy Advisor',
        'brokenEquipment': 'Broken Equipment',
        'firstYear': 'First Year'
    }
    for status_id in vs.get_all_status():
        statuses.append({
            'id': status_id,
            'name': status_display_names.get(status_id, status_id.replace('_', ' ').title()),
            'description': status_descriptions.get(status_id, '')
        })
    
    # Get available actions
    actions = get_available_actions(engine)
    
    # V1.4: Calculate total months elapsed
    year = stats['year']
    month = stats['month']
    total_months = (year - 1) * 12 + (month - 9 + 1) if month >= 9 else (year - 1) * 12 + (12 - 9 + month + 1)
    
    # V1.4: Get advisor happiness
    advisor_happiness = int(vs.get_var('advisor.happiness', 50))
    
    return {
        'year': stats['year'],
        'month': stats['month'],
        'monthName': get_month_name(stats['month']),
        'morale': stats['hope'],
        'papers': stats['papers_published'],
        'papersRequired': stats['papers_required'],
        'totalMonths': total_months,
        'advisorHappiness': advisor_happiness,
        'items': items,
        'statuses': statuses,
        'actions': actions,
        'isRunning': engine.is_running,
        'isEnded': engine.is_ended,
        'endState': {
            'won': engine.end_state.won,
            'reason': engine.end_state.reason,
            'message': engine.end_state.message
        } if engine.is_ended else None
    }


def get_month_name(month):
    """Get month name from number."""
    months = ["", "January", "February", "March", "April", "May", "June",
              "July", "August", "September", "October", "November", "December"]
    return months[month] if 1 <= month <= 12 else "???"


def get_available_actions(engine):
    """Get list of available actions based on game state."""
    vs = engine.variable_store
    actions = []
    
    # Read Papers is always available
    actions.append({'id': 'read', 'name': '📚 Read Papers', 'description': 'Search for new research ideas'})
    
    if vs.get_item_count('idea') > 0:
        actions.append({'id': 'work_idea', 'name': '💡 Work on Idea', 'description': 'Develop your idea into preliminary results'})
    
    if vs.get_item_count('preliminary_result') > 0:
        actions.append({'id': 'work_preliminary', 'name': '🔬 Work on Preliminary', 'description': 'Turn preliminary into major results'})
    
    # Show figures action but indicate if blocked
    if vs.get_item_count('major_result') > 0:
        if vs.has_status('brokenEquipment'):
            actions.append({'id': 'work_figures_blocked', 'name': '📊 Work on Figures', 'description': '⚠️ BLOCKED - Equipment broken!', 'disabled': True})
        else:
            actions.append({'id': 'work_figures', 'name': '📊 Work on Figures', 'description': 'Create figures for your paper'})
    
    if vs.get_item_count('major_result') > 0 and vs.get_item_count('figure') >= 3:
        actions.append({'id': 'write_paper', 'name': '📝 Write Paper', 'description': 'Write and submit your paper'})
    
    if vs.get_item_count('rejected_paper') > 0:
        actions.append({'id': 'revise', 'name': '✏️ Revise Paper', 'description': 'Revise and resubmit rejected paper'})
    
    # Thesis
    papers_required = int(vs.get_var('rule.papersRequired'))
    if vs.get_item_count('paper') >= papers_required:
        actions.append({'id': 'thesis', 'name': '🎓 Work on Thesis', 'description': 'Defend your thesis and graduate!'})
    
    # Other actions
    actions.append({'id': 'slack', 'name': '😴 Slack Off', 'description': 'Take a break and recover morale'})
    actions.append({'id': 'conference', 'name': '🎤 Attend Conference', 'description': 'Network and get ideas (35% idea chance)'})
    
    # Qual prep
    year = vs.get_var('year')
    month = vs.get_var('month')
    quals_not_yet = (year == 1) or (year == 2 and month < 9)
    if quals_not_yet:
        level = int(vs.get_var('player.qualifyLevel'))
        actions.append({'id': 'quals', 'name': f'📖 Prepare for Quals ({level}/3)', 'description': 'Study for qualifying exam'})
    
    actions.append({'id': 'advance', 'name': '⏩ Next Month', 'description': 'Advance to the next month'})
    
    return actions


@app.route('/')
def index():
    """Main game page."""
    return render_template('index.html')


@app.route('/api/start', methods=['POST'])
def start_game():
    """Start a new game."""
    engine = get_engine()
    engine.start(new_seed=True)
    return jsonify(get_game_state(engine))


@app.route('/api/state', methods=['GET'])
def get_state():
    """Get current game state."""
    engine = get_engine()
    return jsonify(get_game_state(engine))


@app.route('/api/action', methods=['POST'])
def perform_action():
    """Perform a game action."""
    engine = get_engine()
    action = request.json.get('action')
    
    result = {'message': '', 'success': True}
    vs = engine.variable_store
    
    if action == 'read':
        vs.add_var('player.readPapers', 1)
        if engine._random() < 0.4:
            vs.add_item('idea', 1)
            result['message'] = "💡 After reading several papers, you have a new research idea!"
        else:
            result['message'] = "📚 You read some papers. No ideas yet, but you're learning..."
        if engine._random() < 0.05:
            vs.add_status('exhaustion')
            result['message'] += "\n😫 All that reading has left you exhausted..."
        engine.advance_month()
    
    elif action == 'work_idea':
        if engine._random() < 0.45:
            vs.remove_item('idea', 1)
            vs.add_item('preliminary_result', 1)
            result['message'] = "🎉 Success! You've made a Preliminary Result!"
        else:
            result['message'] = "😔 You worked hard but didn't make progress this month..."
        engine.advance_month()
    
    elif action == 'work_preliminary':
        if engine._random() < 0.35:
            vs.remove_item('preliminary_result', 1)
            vs.add_item('major_result', 1)
            result['message'] = "🎉 Success! You've made a Major Result!"
        else:
            result['message'] = "😔 You worked hard but didn't make progress this month..."
        engine.advance_month()
    
    elif action == 'work_figures':
        if engine._random() < 0.6:
            vs.add_item('figure', 1)
            count = vs.get_item_count('figure')
            result['message'] = f"📊 You created a figure! ({count}/3 needed for paper)"
        else:
            result['message'] = "😔 The figures didn't come out right. Try again..."
        if engine._random() < 0.05:
            vs.add_status('brokenEquipment')
            result['message'] += "\n⚠️ Your equipment just broke down!"
        engine.advance_month()
    
    elif action == 'write_paper':
        vs.remove_item('major_result', 1)
        vs.remove_item('figure', 3)
        if engine._random() < 0.6:
            vs.add_item('paper', 1)
            count = vs.get_item_count('paper')
            required = int(vs.get_var('rule.papersRequired'))
            result['message'] = f"🎉 ACCEPTED! Paper published! ({count}/{required} complete)"
            vs.add_var('advisor.happiness', 15)  # Advisor very happy
        else:
            vs.add_item('rejected_paper', 1)
            result['message'] = "😢 REJECTED. The reviewers were not convinced. You can revise."
        engine.advance_month()
    
    elif action == 'revise':
        vs.remove_item('rejected_paper', 1)
        if engine._random() < 0.7:
            vs.add_item('paper', 1)
            count = vs.get_item_count('paper')
            required = int(vs.get_var('rule.papersRequired'))
            result['message'] = f"🎉 ACCEPTED on revision! ({count}/{required} complete)"
        else:
            vs.add_item('rejected_paper', 1)
            result['message'] = "😢 Rejected again... Keep trying!"
        engine.advance_month()
    
    elif action == 'slack':
        hope_gain = 5 + int(engine._random() * 10)
        vs.add_var('player.hope', hope_gain)
        vs.add_var('advisor.happiness', -5)  # Advisor not happy about slacking
        result['message'] = f"😌 You took some time to relax. (+{hope_gain} morale)"
        if vs.has_status('exhaustion') and engine._random() < 0.35:
            vs.remove_status('exhaustion')
            result['message'] += "\n💆 You're feeling refreshed! Exhaustion has faded."
        if vs.has_status('unhappyAdvisor') and engine._random() < 0.25:
            vs.remove_status('unhappyAdvisor')
            result['message'] += "\n🤝 Your advisor seems to have cooled down."
        if not vs.has_status('unhappyAdvisor') and engine._random() < 0.1:
            vs.add_status('unhappyAdvisor')
            result['message'] += "\n😠 Your advisor noticed you weren't working..."
        engine.advance_month()
    
    elif action == 'quals':
        # V1.4: Randomize qual prep - adds 0-2 points per session
        points_gained = int(engine._random() * 3)  # 0, 1, or 2
        vs.add_var('player.qualifyLevel', points_gained)
        level = int(vs.get_var('player.qualifyLevel'))
        if points_gained == 0:
            result['message'] = f"📖 You studied but didn't retain much. (Preparation: {level}/3)"
        elif points_gained == 1:
            result['message'] = f"📖 Decent study session! (Preparation: {level}/3)"
        else:
            result['message'] = f"📖 Great progress! (Preparation: {level}/3)"
        engine.advance_month()
    
    elif action == 'thesis':
        result['message'] = "📚 It's time to write your thesis and defend!"
        result['showThesisChoice'] = True
    
    elif action == 'thesis_defend':
        if engine._random() < 0.9:
            result['message'] = "🎓🎉 CONGRATULATIONS, DOCTOR! 🎉🎓\n\nYou've successfully defended your thesis!"
            engine._ended = True
            engine._running = False
            engine._end_state = EndGameState(True, "graduation", "You are now Dr. You!")
        else:
            result['message'] = "😅 The defense was rough, but you passed with major revisions!"
            engine._ended = True
            engine._running = False
            engine._end_state = EndGameState(True, "graduation", "It wasn't easy, but you made it!")
    
    elif action == 'thesis_stay':
        vs.add_var('player.hope', 20)
        vs.add_var('advisor.happiness', 10)  # Advisor pleased
        result['message'] = "You decide to stay and do more research. Your advisor is pleased. (+20 morale)"
        engine.advance_month()
    
    elif action == 'advance':
        engine.advance_month()
        result['message'] = "Time passes..."
    
    # V1.5: New conference action
    elif action == 'conference':
        vs.add_var('player.hope', 8)  # Networking boost
        result['message'] = "🎤 You attended a conference and met interesting researchers! (+8 morale)"
        if engine._random() < 0.35:
            vs.add_item('idea', 1)
            result['message'] += "\n💡 The talks inspired a new research idea!"
        if engine._random() < 0.1:
            vs.add_var('advisor.happiness', 10)
            result['message'] += "\n🤝 Your advisor heard good things about your presentation!"
        engine.advance_month()
    
    # V1.5: Handle equipment repair at end of actions
    if vs.has_status('brokenEquipment'):
        broken_months = int(vs.get_var('equipment.brokenMonths', 0)) + 1
        vs.set_var('equipment.brokenMonths', broken_months)
        if broken_months >= 3:
            vs.remove_status('brokenEquipment')
            vs.set_var('equipment.brokenMonths', 0)
            result['message'] += "\n\n🔧 After 3 months, the equipment has finally been fixed!"
        elif engine._random() < 0.5:
            vs.remove_status('brokenEquipment')
            vs.set_var('equipment.brokenMonths', 0)
            result['message'] += "\n\n🔧 Good news! The equipment has been fixed."
    
    # Process events (skip Switch/CoinFlip since we handle them manually)
    while True:
        context = engine.tick()
        if context is None:
            break
        if context.pending_message:
            result['message'] += f"\n\n{context.pending_message}"
    
    state = get_game_state(engine)
    state['result'] = result
    return jsonify(state)


@app.route('/api/restart', methods=['POST'])
def restart_game():
    """Restart the game."""
    session_id = session.get('session_id')
    if session_id and session_id in game_engines:
        del game_engines[session_id]
    return start_game()


@app.route('/api/save', methods=['GET'])
def save_game():
    """Return game state for saving to localStorage."""
    engine = get_engine()
    vs = engine.variable_store
    
    save_data = {
        'variables': dict(vs._variables) if hasattr(vs, '_variables') else {},
        'items': dict(vs.get_all_items()),
        'statuses': list(vs.get_all_status()),
        'eventsFired': list(engine.event_engine._fired_events) if hasattr(engine.event_engine, '_fired_events') else [],
        'isRunning': engine._running,
        'isEnded': engine._ended,
        'version': '1.6'
    }
    
    return jsonify(save_data)


@app.route('/api/load', methods=['POST'])
def load_game():
    """Load game state from save data."""
    engine = get_engine()
    vs = engine.variable_store
    save_data = request.json
    
    if not save_data or save_data.get('version') != '1.6':
        return jsonify({'error': 'Invalid save data'}), 400
    
    # Restore variables
    if hasattr(vs, '_variables'):
        vs._variables.clear()
        vs._variables.update(save_data.get('variables', {}))
    
    # Restore items
    vs._items = save_data.get('items', {})
    
    # Restore statuses
    vs._active_statuses = set(save_data.get('statuses', []))
    
    # Restore engine state
    engine._running = save_data.get('isRunning', True)
    engine._ended = save_data.get('isEnded', False)
    
    # Restore fired events
    if hasattr(engine.event_engine, '_fired_events'):
        engine.event_engine._fired_events = set(save_data.get('eventsFired', []))
    
    return jsonify({'success': True, **get_game_state(engine)})


def run_server(host='127.0.0.1', port=5000, debug=False):
    """Run the web server."""
    print(f"\n🎓 GradQuest Web UI running at http://{host}:{port}\n")
    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    run_server(debug=True)
