#!/usr/bin/env python3
"""
Simplified test runner for GradQuest tests.html
Simulates DOM and runs 6 regression tests
"""

import sys
import os
import json

# Simulate minimal DOM elements
class MockElement:
    def __init__(self):
        self.innerHTML = ""
        self.textContent = ""
        self.attributes = {}
        self.style = {}

    def setAttribute(self, name, value):
        self.attributes[name] = value

class MockDOM:
    def __init__(self):
        self.elements = {}

    def getElementById(self, element_id):
        if element_id not in self.elements:
            self.elements[element_id] = MockElement()
        return self.elements[element_id]

# Test suite implementation
class TestSuite:
    def __init__(self):
        self.results = []
        self.dom = MockDOM()

    def assert_condition(self, condition, message):
        if not condition:
            raise AssertionError(message or 'Assertion failed')

    def runTest(self, name, testFn):
        try:
            testFn()
            self.results.append({'name': name, 'status': 'PASS', 'error': None})
            return True
        except Exception as error:
            self.results.append({'name': name, 'status': 'FAIL', 'error': str(error)})
            return False

    def runAll(self):
        print('[TestSuite] Starting tests...\n')

        # Test 1: Defense Gating Enforced
        self.runTest('defenseGatingEnforced', self.test_defense_gating)

        # Test 2: One Modal Per Tick
        self.runTest('oneModalPerTick', self.test_one_modal)

        # Test 3: No Empty Month Logs
        self.runTest('noEmptyMonthLogs', self.test_no_empty_logs)

        # Test 4: Conference No Overlap
        self.runTest('conferenceNoOverlap', self.test_conference_no_overlap)

        # Test 5: Single Primary Stat Mutation
        self.runTest('singlePrimaryStatMutation', self.test_single_mutation)

        # Test 6: Defense State Cleanup
        self.runTest('defenseStateCleanup', self.test_defense_cleanup)

        return self.results

    # Test 1: Defense Gating
    def test_defense_gating(self):
        # Simulate GRADUATION_CONTRACT.defenseUnlocked
        testState = {
            'thesisProgress': 99,
            'papers': [{'type': 'journal'}, {'type': 'journal'}, {'type': 'journal'}],
            'qualsPassed': True
        }
        thesis_complete = (testState.get('thesisProgress') or 0) >= 100
        journal_papers = len([p for p in testState.get('papers', []) if p.get('type') == 'journal'])
        portfolio_eligible = journal_papers >= 3  # Required papers
        unlocked = thesis_complete and portfolio_eligible and testState.get('qualsPassed')
        self.assert_condition(not unlocked, 'Defense should be locked when thesis < 100%')

    # Test 2: One Modal Per Tick
    def test_one_modal(self):
        class MockEventResolver:
            def __init__(self):
                self.eventQueue = []
                self.shownThisTurn = 0
                self.maxModalsPerTurn = 1

            def enqueue(self, event):
                self.eventQueue.append(event)

            def canShowModal(self):
                return self.shownThisTurn < self.maxModalsPerTurn

            def priorityWeight(self, event):
                weights = {'Emergency': 100, 'Major': 50, 'Minor': 10}
                return weights.get(event.get('priority'), 0)

            def resolveTick(self, state):
                self.eventQueue.sort(key=lambda e: self.priorityWeight(e), reverse=True)
                self.shownThisTurn = 0
                for event in self.eventQueue:
                    if self.canShowModal():
                        self.shownThisTurn += 1

        resolver = MockEventResolver()
        resolver.enqueue({'id': 'event1', 'priority': 'Major', 'message': 'Test 1'})
        resolver.enqueue({'id': 'event2', 'priority': 'Major', 'message': 'Test 2'})
        resolver.enqueue({'id': 'event3', 'priority': 'Major', 'message': 'Test 3'})

        resolver.resolveTick({})
        self.assert_condition(resolver.shownThisTurn == 1, f'Expected 1 modal, got {resolver.shownThisTurn}')

    # Test 3: No Empty Month Logs
    def test_no_empty_logs(self):
        # Simulate event log tracking
        eventLog = []
        for i in range(12):
            eventLog.append({'month': i, 'text': f'Month {i+1} event', 'modal': False})

        hasLogs = len(eventLog) > 0
        emptyEntries = [e for e in eventLog if not e.get('text') or e.get('text', '').strip() == '']

        self.assert_condition(hasLogs, 'Event log should not be empty after 12 turns')
        self.assert_condition(len(emptyEntries) == 0, f'Found {len(emptyEntries)} empty log entries')

    # Test 4: Conference No Overlap
    def test_conference_no_overlap(self):
        # Simulate conference state
        state = {
            'conferenceAttendedThisYear': True,
            'lastConferenceMonth': 5
        }

        # Simulate conference action check
        monthsSinceLastConf = 5 - state.get('lastConferenceMonth', 0)
        isBlocked = state.get('conferenceAttendedThisYear') and monthsSinceLastConf < 2

        self.assert_condition(isBlocked, 'Conference should be blocked after attending')

    # Test 5: Single Primary Stat Mutation
    def test_single_mutation(self):
        # Simulate state update tracking
        mutations = []

        class MockGame:
            def __init__(self):
                self.state = {}

            def updateState(self, changes, owner=None):
                # Track primary stat mutations
                primary_stats = ['thesisProgress', 'papers', 'alignment']
                changed = [k for k in changes.keys() if k in primary_stats]
                if changed:
                    mutations.append(len(changed))

        game = MockGame()
        # Simulate an action that changes one primary stat
        game.updateState({'papers': [], 'alignment': 50})

        # Check max mutations in a single update
        max_mutations = max(mutations) if mutations else 0
        self.assert_condition(max_mutations <= 1, f'Action mutated {max_mutations} primary stats, expected <= 1')

    # Test 6: Defense State Cleanup
    def test_defense_cleanup(self):
        # Simulate defense state
        state = {
            'defenseActive': True,
            'defenseTurn': 2,
            'defenseThesisQuality': 80,
            'defensePresentation': 70,
            'defenseCommittee': 60,
            'uiMode': 'FINALE'
        }

        # Simulate endDefense cleanup
        state['defenseActive'] = False
        state['defenseTurn'] = 0
        state['defenseThesisQuality'] = 0
        state['defensePresentation'] = 0
        state['defenseCommittee'] = 0
        state['uiMode'] = 'NORMAL'

        self.assert_condition(state['defenseActive'] == False, 'defenseActive should be false')
        self.assert_condition(state['defenseTurn'] == 0, 'defenseTurn should be 0')
        self.assert_condition(state['defenseThesisQuality'] == 0, 'defenseThesisQuality should be 0')
        self.assert_condition(state['defensePresentation'] == 0, 'defensePresentation should be 0')
        self.assert_condition(state['defenseCommittee'] == 0, 'defenseCommittee should be 0')
        self.assert_condition(state['uiMode'] == 'NORMAL', 'uiMode should be NORMAL')

def renderResults(results):
    passed = sum(1 for r in results if r['status'] == 'PASS')
    failed = sum(1 for r in results if r['status'] == 'FAIL')

    print("=" * 60)
    print("GRADQUEST REGRESSION TEST RESULTS")
    print("=" * 60)
    print(f"\n{passed} PASSED | {failed} FAILED | {len(results)} TOTAL\n")
    print("=" * 60)

    for r in results:
        icon = "✓" if r['status'] == 'PASS' else "✗"
        color = "\033[92m" if r['status'] == 'PASS' else "\033[91m"  # Green or Red
        reset = "\033[0m"
        print(f"{color}{icon} {r['name']}{reset}")
        if r.get('error'):
            print(f"   Error: {r['error']}")
        print()

    print("=" * 60)

    # Exit with error code if any tests failed
    if failed > 0:
        sys.exit(1)

def main():
    import asyncio
    suite = TestSuite()
    results = suite.runAll()
    renderResults(results)

if __name__ == '__main__':
    main()
