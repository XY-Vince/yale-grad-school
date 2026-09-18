#!/usr/bin/env python3
from pathlib import Path
"""
smart_playtest.py - Competent Human Player Simulation for V2.59.2 Balance Testing

This script simulates a competent human player to test GradQuest V2.59.2 balance changes.
It follows a priority-based decision system:
1. Survival First (morale management)
2. Career Second (advisor tension management)
3. Pipeline Third (research progression)
4. Safe Event Choices (minimize variance)
"""

import asyncio
import json
import statistics
import argparse
import sys
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from datetime import datetime
from playwright.async_api import async_playwright


@dataclass
class RunTelemetry:
    """Per-run telemetry data"""
    run_number: int
    months_survived: int = 0
    end_reason: str = "Unknown"
    papers_published: int = 0
    lowest_morale: int = 100
    exhaustion_count: int = 0
    specialization: str = ""
    thesis_progress: int = 0
    final_morale: int = 0
    advisor_tension: int = 0
    notes: List[str] = field(default_factory=list)


@dataclass
class GlobalStats:
    """Global statistics across all runs"""
    total_runs: int = 0
    wins: int = 0
    losses: int = 0
    timeouts: int = 0
    median_duration: float = 0.0
    win_rate: float = 0.0
    avg_papers: float = 0.0
    avg_lowest_morale: float = 0.0


class SmartPlaytester:
    """
    Simulates a competent human player with smart decision-making.
    
    Decision Priority:
    1. Survival: If Morale < 35 (or < 45 if Exhausted), prioritize break
    2. Career: If Advisor Tension > 50, prioritize pitch session
    3. Pipeline: Follow research pipeline logic
    4. Events: Safe/polite choices to minimize variance
    """
    
    def __init__(self):
        self.results: List[RunTelemetry] = []
        self.global_stats = GlobalStats()
        self.timeout_minutes = 10
        
    async def play_game(self, run_number: int) -> RunTelemetry:
        """Play a single game simulation"""
        telemetry = RunTelemetry(run_number=run_number)
        specs = ['experimentalist', 'theoretician', 'computational']
        telemetry.specialization = specs[run_number % 3]
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(viewport={'width': 1280, 'height': 800})
            
            # Load game
            await page.goto(f'file://{Path(__file__).resolve().parent}/docs/index.html')
            await page.wait_for_selector('#start-screen', timeout=10000)
            
            # Select specialization and start
            await page.click(f'#spec-{telemetry.specialization}')
            await page.wait_for_timeout(400)
            await page.click('#start-game-btn')
            await page.wait_for_timeout(1000)
            
            # Track exhaustion state
            was_exhausted = False
            
            # Main game loop
            max_turns = 300
            for turn in range(max_turns):
                # Check for game end
                end_screen = await page.query_selector('#end-screen')
                if end_screen and await end_screen.is_visible():
                    title = await page.text_content('#end-title') or ""
                    telemetry.end_reason = self._parse_ending(title)
                    stats_text = await page.text_content('#end-stats') or ""
                    telemetry.notes.append(stats_text[:150])
                    break
                
                # Get current game state
                state = await self._get_game_state(page)
                
                # Update telemetry
                telemetry.months_survived = state['months']
                telemetry.papers_published = state['papers']
                telemetry.thesis_progress = state.get('thesis_progress', 0)
                telemetry.final_morale = state['morale']
                telemetry.advisor_tension = state.get('advisor_tension', 0)
                
                if state['morale'] < telemetry.lowest_morale:
                    telemetry.lowest_morale = state['morale']
                
                # Track exhaustion
                if state.get('exhausted', False):
                    if not was_exhausted:
                        telemetry.exhaustion_count += 1
                        was_exhausted = True
                else:
                    was_exhausted = False
                
                # Handle any visible modals first
                modal_handled = await self._handle_modals(page)
                if modal_handled:
                    await page.wait_for_timeout(300)
                    continue
                
                # Make smart decision based on state
                action_taken = await self._make_smart_decision(page, state)
                
                if not action_taken:
                    # Fallback: try any available action
                    await page.evaluate('''() => {
                        const btns = document.querySelectorAll('#actions .action-btn:not(.disabled)');
                        if (btns.length > 0) btns[0].click();
                    }''')
                
                await page.wait_for_timeout(400)
                
                # Progress logging
                if turn < 5 or turn % 20 == 0:
                    print(f"  Run {run_number} - Turn {turn}: Month {state['months']}, "
                          f"Morale {state['morale']}, Papers {state['papers']}, "
                          f"Tension {state.get('advisor_tension', 0)}, "
                          f"Pipeline: {state.get('debug_pipeline', '')[:50]}...")
            
            if telemetry.end_reason == "Unknown":
                telemetry.end_reason = "Timeout"
            
            await browser.close()
        
        return telemetry
    
    async def _get_game_state(self, page) -> Dict[str, Any]:
        """Extract current game state from the page"""
        return await page.evaluate('''() => {
            const moraleBar = document.getElementById('morale-bar');
            const advisorBar = document.getElementById('advisor-bar');
            const tensionEl = document.getElementById('advisor-tension');
            const stressEl = document.getElementById('stress-state');
            const statuses = document.getElementById('statuses');
            
            // Check for exhaustion status
            let exhausted = false;
            if (statuses) {
                const statusBadges = statuses.querySelectorAll('.status-badge');
                statusBadges.forEach(badge => {
                    if (badge.textContent.toLowerCase().includes('exhaust')) {
                        exhausted = true;
                    }
                });
            }
            
            // Parse tension from text
            let tension = 0;
            if (tensionEl) {
                const tensionText = tensionEl.textContent || '';
                if (tensionText.includes('Furious') || tensionText.includes('😡')) tension = 80;
                else if (tensionText.includes('Frustrated') || tensionText.includes('😤')) tension = 60;
                else if (tensionText.includes('Concerned') || tensionText.includes('😐')) tension = 35;
                else if (tensionText.includes('Pleased') || tensionText.includes('😊')) tension = 15;
                else tension = 25; // Neutral
            }
            
            // Get thesis progress from graduation card
            let thesisProgress = 0;
            const thesisProgressEl = document.getElementById('thesis-progress');
            if (thesisProgressEl) {
                const match = thesisProgressEl.textContent.match(/(\d+)%/);
                if (match) thesisProgress = parseInt(match[1]);
            }
            
            // Get figures count from pipeline
            let figures = 0;
            let ideas = 0;
            let initial_findings = 0;
            let key_discovery = 0;
            
            // Get Quals level
            let qualifyLevel = 0;
            const qualsEl = document.getElementById('quals-prep-value');
            if (qualsEl) qualifyLevel = parseInt(qualsEl.textContent) || 0;
            
            const pipeline = document.getElementById('pipeline');
            if (pipeline) {
                const text = pipeline.textContent || '';
                // Parse pipeline items
                // V2.59 Update: Icons changed (Ideas=📚) and format is now "Icon Label ×Count" (e.g. "📚 Ideas ×1")
                
                const ideaMatch = text.match(/[📚💡]\s*Ideas?\s*[×x]\s*(\d+)/);
                if (ideaMatch) ideas = parseInt(ideaMatch[1]);
                
                const findingsMatch = text.match(/🔬\s*Findings?\s*[×x]\s*(\d+)/);
                if (findingsMatch) initial_findings = parseInt(findingsMatch[1]);
                
                const discoveryMatch = text.match(/🎯\s*Discover(y|ies)?\s*[×x]\s*(\d+)/);
                if (discoveryMatch) key_discovery = parseInt(discoveryMatch[2] || discoveryMatch[1]);
                
                const figuresMatch = text.match(/📊\s*Figures?\s*[×x]\s*(\d+)/);
                if (figuresMatch) figures = parseInt(figuresMatch[1]);
            }
            
            return {
                morale: moraleBar ? (parseInt(moraleBar.style.width) || 50) : 50,
                papers: parseInt(document.getElementById('papers')?.textContent || '0'),
                months: parseInt(document.getElementById('total-months')?.textContent || '1'),
                thesis_progress: thesisProgress,
                advisor_tension: tension,
                exhausted: exhausted,
                figures: figures,
                ideas: ideas,
                initial_findings: initial_findings,
                key_discovery: key_discovery,
                qualifyLevel: qualifyLevel,
                message: document.getElementById('message-log')?.textContent || '',
                debug_pipeline: document.getElementById('pipeline')?.textContent || 'NO_PIPELINE'
            };
        }''')
    
    async def _handle_modals(self, page) -> bool:
        """Handle any visible modals. Returns True if a modal was handled."""
        return await page.evaluate('''() => {
            // Event modal (centered)
            const eventModal = document.getElementById('event-modal');
            if (eventModal && eventModal.style.display !== 'none') {
                const btn = eventModal.querySelector('.event-modal-btn');
                if (btn) {
                    btn.click();
                    return true;
                }
            }
            
            // Thesis modal
            const thesisModal = document.getElementById('thesis-modal');
            if (thesisModal && thesisModal.classList.contains('active')) {
                // For thesis modal, click "Defend Thesis" if available (we're ready)
                const defendBtn = thesisModal.querySelector('.modal-btn.primary');
                if (defendBtn) {
                    defendBtn.click();
                    return true;
                }
                const stayBtn = thesisModal.querySelector('.modal-btn.secondary');
                if (stayBtn) {
                    stayBtn.click();
                    return true;
                }
            }
            
            // Defense modal
            const defenseModal = document.getElementById('defense-modal');
            if (defenseModal && defenseModal.classList.contains('active')) {
                // In defense, click any available action
                const action = defenseModal.querySelector('.defense-action-btn:not(.disabled)');
                if (action) {
                    action.click();
                    return true;
                }
                const resultBtn = defenseModal.querySelector('.defense-result .modal-btn');
                if (resultBtn) {
                    resultBtn.click();
                    return true;
                }
            }
            
            return false;
        }''')
    
    async def _make_smart_decision(self, page, state: Dict[str, Any]) -> bool:
        """
        Make a smart decision based on game state.
        Returns True if an action was taken.
        
        Priority:
        1. Survival: Morale < 35 (or < 45 if Exhausted) -> Take Break
        2. Career: Advisor Tension > 50 -> Pitch Session
        3. Pipeline: Follow research progression
        4. Safe choices for events
        """
        morale = state['morale']
        exhausted = state.get('exhausted', False)
        tension = state.get('advisor_tension', 0)
        papers = state['papers']
        thesis_progress = state.get('thesis_progress', 0)
        figures = state.get('figures', 0)
        ideas = state.get('ideas', 0)
        initial_findings = state.get('initial_findings', 0)
        key_discovery = state.get('key_discovery', 0)
        qualifyLevel = state.get('qualifyLevel', 0)
        months = state.get('months', 1)
        
        # Priority 1: Survival - Check morale thresholds
        morale_threshold = 45 if exhausted else 35
        if morale < morale_threshold:
            return await self._click_action(page, ['Break', 'Time Of', 'Medical Leave'])
        
        # Priority 1.5: Quals - If not passed (level < 3) and time is passing (Month > 6)
        # Assuming we want to pass by Month 13.
        if qualifyLevel < 3 and months >= 6:
             if await self._click_action(page, ['Study for Quals', 'Study']):
                 return True
        
        # Priority 1.6: Revisions - Always prioritize clearing the queue
        if await self._click_action(page, ['Major Revision', 'Resubmit Paper', 'Revise Paper', 'Address Reviewers']):
            return True
        
        # Priority 2: Career - Check advisor tension
        if tension > 50:
            return await self._click_action(page, ['Pitch Session', 'Meet Advisor'])
        
        # Priority 3: Pipeline - Research progression logic
        # Check if we can defend (3 papers + 100% thesis)
        if papers >= 2 and thesis_progress >= 100:
            if await self._click_action(page, ['Prepare Defense', 'Defend Thesis', 'Defend']):
                return True
        
        # If we have 3 papers but thesis not complete, prioritize thesis
        if papers >= 3 and thesis_progress < 100:
            if await self._click_action(page, ['Write Thesis', 'Write Dissertation']):
                return True
        
        # If we have enough figures, draft paper
        if figures >= 3:
            if await self._click_action(page, ['Journal Paper', 'Conference Paper', 'Draft Paper', 'Submit Paper']):
                return True
        
        # If we have key discovery but not enough figures, work on figures
        if key_discovery >= 1 and figures < 3:
            if await self._click_action(page, ['Validate Discovery', 'Make Figures', 'Document Findings', 'Work Figures']):
                return True
        
        # If we have initial findings, develop them
        if initial_findings >= 1:
            if await self._click_action(page, ['Develop Findings']):
                return True
        
        # If we have ideas, work on them
        if ideas >= 1:
            if await self._click_action(page, ['Work on Idea', 'Develop Idea']):
                return True
        
        # Default: Read papers to get ideas
        if await self._click_action(page, ['Read Papers']):
            return True
        
        # Fallback: Try any action
        return await self._click_action(page, [])
    
    async def _click_action(self, page, priorities: List[str]) -> bool:
        """Click an action button based on priority list"""
        if not priorities:
            # Fallback: click first available
            return await page.evaluate('''() => {
                const btns = document.querySelectorAll('#actions .action-btn:not(.disabled)');
                if (btns.length > 0) {
                    btns[0].click();
                    return true;
                }
                return false;
            }''')
        
        # Try each priority in order
        for priority in priorities:
            clicked = await page.evaluate(f'''() => {{
                const btns = document.querySelectorAll('#actions .action-btn:not(.disabled)');
                for (const b of btns) {{
                    if (b.textContent.includes('{priority}')) {{
                        b.click();
                        return true;
                    }}
                }}
                return false;
            }}''')
            if clicked:
                return True
        
        return False
    
    def _parse_ending(self, text: str) -> str:
        """Parse the ending type from end screen title"""
        t = (text or "").lower()
        if 'phd' in t or 'doctorate' in t or 'congratulations' in t or 'distinction' in t:
            return 'PhD'
        if 'master' in t:
            return "Master's"
        if 'drop' in t or 'quit' in t or 'game over' in t:
            return 'Dropout'
        if 'time' in t:
            return 'Timeout'
        return 'Unknown'
    
    async def run(self, num_runs: int = 10):
        """Run multiple game simulations"""
        print(f"\n{'='*70}")
        print(f"SMART PLAYTEST - V2.59.2 Balance Verification")
        print(f"Simulating {num_runs} competent human player runs")
        print(f"Timeout: {self.timeout_minutes} minutes per run")
        print(f"{'='*70}\n")
        
        self.results = []
        
        for i in range(1, num_runs + 1):
            print(f"\n[Run {i}/{num_runs}] Starting...")
            try:
                telemetry = await self.play_game(i)
                self.results.append(telemetry)
                print(f"[Run {i}] COMPLETE: {telemetry.end_reason} | "
                      f"{telemetry.months_survived}mo | "
                      f"{telemetry.papers_published} papers | "
                      f"Lowest morale: {telemetry.lowest_morale}")
            except Exception as e:
                print(f"[Run {i}] ERROR: {str(e)[:100]}")
                # Create error result
                error_telemetry = RunTelemetry(
                    run_number=i,
                    end_reason=f"Error: {str(e)[:50]}",
                    notes=[str(e)]
                )
                self.results.append(error_telemetry)
        
        # Calculate global stats
        self._calculate_global_stats()
        
        print(f"\n{'='*70}")
        print("ALL RUNS COMPLETE")
        print(f"{'='*70}")
    
    def _calculate_global_stats(self):
        """Calculate global statistics from all runs"""
        completed_runs = [r for r in self.results if not r.end_reason.startswith('Error')]
        
        if not completed_runs:
            return
        
        self.global_stats.total_runs = len(completed_runs)
        
        # Count outcomes
        for r in completed_runs:
            if r.end_reason == 'PhD':
                self.global_stats.wins += 1
            elif r.end_reason == 'Timeout':
                self.global_stats.timeouts += 1
            else:
                self.global_stats.losses += 1
        
        # Calculate rates
        self.global_stats.win_rate = (self.global_stats.wins / len(completed_runs)) * 100
        
        # Calculate medians and averages
        durations = [r.months_survived for r in completed_runs]
        papers = [r.papers_published for r in completed_runs]
        lowest_morales = [r.lowest_morale for r in completed_runs]
        
        if durations:
            self.global_stats.median_duration = statistics.median(durations)
        if papers:
            self.global_stats.avg_papers = statistics.mean(papers)
        if lowest_morales:
            self.global_stats.avg_lowest_morale = statistics.mean(lowest_morales)
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive JSON report"""
        completed_runs = [r for r in self.results if not r.end_reason.startswith('Error')]
        
        # Per-run details
        run_details = []
        for r in completed_runs:
            run_details.append({
                'run_number': r.run_number,
                'months_survived': r.months_survived,
                'end_reason': r.end_reason,
                'papers_published': r.papers_published,
                'thesis_progress': r.thesis_progress,
                'lowest_morale': r.lowest_morale,
                'final_morale': r.final_morale,
                'exhaustion_count': r.exhaustion_count,
                'advisor_tension': r.advisor_tension,
                'specialization': r.specialization,
                'notes': r.notes
            })
        
        # Outcome distribution
        outcomes = {}
        for r in completed_runs:
            outcomes[r.end_reason] = outcomes.get(r.end_reason, 0) + 1
        
        # Specialization performance
        spec_stats = {}
        for r in completed_runs:
            if r.specialization not in spec_stats:
                spec_stats[r.specialization] = {'runs': 0, 'wins': 0, 'avg_months': []}
            spec_stats[r.specialization]['runs'] += 1
            if r.end_reason == 'PhD':
                spec_stats[r.specialization]['wins'] += 1
            spec_stats[r.specialization]['avg_months'].append(r.months_survived)
        
        for spec in spec_stats:
            spec_stats[spec]['win_rate'] = (spec_stats[spec]['wins'] / spec_stats[spec]['runs']) * 100
            spec_stats[spec]['avg_duration'] = statistics.mean(spec_stats[spec]['avg_months'])
            del spec_stats[spec]['avg_months']
        
        report = {
            'metadata': {
                'version': 'V2.59.2',
                'test_type': 'Smart Playtest - Competent Human Simulation',
                'timestamp': datetime.now().isoformat(),
                'total_runs': len(completed_runs),
                'timeout_minutes': self.timeout_minutes
            },
            'global_stats': {
                'win_rate_percent': round(self.global_stats.win_rate, 1),
                'median_duration_months': round(self.global_stats.median_duration, 1),
                'avg_papers': round(self.global_stats.avg_papers, 2),
                'avg_lowest_morale': round(self.global_stats.avg_lowest_morale, 1),
                'outcome_distribution': outcomes
            },
            'specialization_performance': spec_stats,
            'per_run_data': run_details,
            'balance_analysis': self._generate_balance_analysis(completed_runs)
        }
        
        return report
    
    def _generate_balance_analysis(self, runs: List[RunTelemetry]) -> Dict[str, Any]:
        """Generate balance analysis based on results"""
        analysis = {
            'pacing': '',
            'difficulty': '',
            'issues': [],
            'recommendations': []
        }
        
        if not runs:
            analysis['issues'].append('No valid runs completed')
            return analysis
        
        durations = [r.months_survived for r in runs]
        avg_duration = statistics.mean(durations)
        median_duration = statistics.median(durations)
        
        # Pacing analysis
        if avg_duration < 50:
            analysis['pacing'] = 'TOO_FAST'
            analysis['issues'].append(f'Average duration {avg_duration:.1f}mo is below target (60-75)')
            analysis['recommendations'].append('Consider increasing research time requirements')
        elif avg_duration > 85:
            analysis['pacing'] = 'TOO_SLOW'
            analysis['issues'].append(f'Average duration {avg_duration:.1f}mo exceeds target (60-75)')
            analysis['recommendations'].append('Consider reducing research time requirements')
        else:
            analysis['pacing'] = 'GOOD'
        
        # Difficulty analysis
        phd_rate = self.global_stats.win_rate
        if phd_rate < 30:
            analysis['difficulty'] = 'TOO_HARD'
            analysis['issues'].append(f'PhD win rate {phd_rate:.1f}% is below target (30-70%)')
            analysis['recommendations'].append('Consider reducing difficulty or adding recovery options')
        elif phd_rate > 70:
            analysis['difficulty'] = 'TOO_EASY'
            analysis['issues'].append(f'PhD win rate {phd_rate:.1f}% exceeds target (30-70%)')
            analysis['recommendations'].append('Consider increasing challenge')
        else:
            analysis['difficulty'] = 'BALANCED'
        
        # Check for exhaustion issues
        avg_exhaustion = statistics.mean([r.exhaustion_count for r in runs])
        if avg_exhaustion > 3:
            analysis['issues'].append(f'High exhaustion rate (avg {avg_exhaustion:.1f} per run)')
            analysis['recommendations'].append('Review stress/morale decay rates')
        
        return analysis
    
    def print_summary(self):
        """Print human-readable summary to console"""
        report = self.generate_report()
        
        print(f"\n{'='*70}")
        print("SMART PLAYTEST SUMMARY - V2.59.2")
        print(f"{'='*70}")
        
        print(f"\n📊 GLOBAL STATISTICS")
        print(f"  Total Runs: {report['metadata']['total_runs']}")
        print(f"  Win Rate: {report['global_stats']['win_rate_percent']}%")
        print(f"  Median Duration: {report['global_stats']['median_duration_months']} months")
        print(f"  Avg Papers: {report['global_stats']['avg_papers']}")
        print(f"  Avg Lowest Morale: {report['global_stats']['avg_lowest_morale']}")
        
        print(f"\n📈 OUTCOME DISTRIBUTION")
        for outcome, count in report['global_stats']['outcome_distribution'].items():
            pct = (count / report['metadata']['total_runs']) * 100
            print(f"  {outcome}: {count} ({pct:.1f}%)")
        
        print(f"\n🔬 SPECIALIZATION PERFORMANCE")
        for spec, stats in report['specialization_performance'].items():
            print(f"  {spec}: {stats['win_rate']:.1f}% win rate, {stats['avg_duration']:.1f}mo avg")
        
        print(f"\n⚖️ BALANCE ANALYSIS")
        analysis = report['balance_analysis']
        print(f"  Pacing: {analysis['pacing']}")
        print(f"  Difficulty: {analysis['difficulty']}")
        
        if analysis['issues']:
            print(f"\n⚠️ ISSUES DETECTED")
            for issue in analysis['issues']:
                print(f"  - {issue}")
        
        if analysis['recommendations']:
            print(f"\n💡 RECOMMENDATIONS")
            for rec in analysis['recommendations']:
                print(f"  - {rec}")
        
        print(f"\n{'='*70}")


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Smart Playtest - GradQuest Balance Testing')
    parser.add_argument('--runs', type=int, default=10, help='Number of game simulations to run (default: 10)')
    parser.add_argument('--timeout', type=int, default=10, help='Timeout in minutes per run (default: 10)')
    args = parser.parse_args()
    
    tester = SmartPlaytester()
    tester.timeout_minutes = args.timeout
    
    await tester.run(num_runs=args.runs)
    
    # Print summary
    tester.print_summary()
    
    # Generate and save JSON report
    report = tester.generate_report()
    
    output_file = f'{Path(__file__).resolve().parent}/smart_playtest_results.json'
    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n✅ Full report saved to: {output_file}")
    
    # Also save a summary markdown file
    md_file = f'{Path(__file__).resolve().parent}/smart_playtest_summary.md'
    with open(md_file, 'w') as f:
        f.write(f"# Smart Playtest Results - V2.59.2\n\n")
        f.write(f"**Date:** {report['metadata']['timestamp']}\n\n")
        f.write(f"**Total Runs:** {report['metadata']['total_runs']}\n\n")
        
        f.write(f"## Global Statistics\n\n")
        f.write(f"- **Win Rate:** {report['global_stats']['win_rate_percent']}%\n")
        f.write(f"- **Median Duration:** {report['global_stats']['median_duration_months']} months\n")
        f.write(f"- **Avg Papers:** {report['global_stats']['avg_papers']}\n")
        f.write(f"- **Avg Lowest Morale:** {report['global_stats']['avg_lowest_morale']}\n\n")
        
        f.write(f"## Outcome Distribution\n\n")
        for outcome, count in report['global_stats']['outcome_distribution'].items():
            pct = (count / report['metadata']['total_runs']) * 100
            f.write(f"- {outcome}: {count} ({pct:.1f}%)\n")
        
        f.write(f"\n## Balance Analysis\n\n")
        analysis = report['balance_analysis']
        f.write(f"- **Pacing:** {analysis['pacing']}\n")
        f.write(f"- **Difficulty:** {analysis['difficulty']}\n")
        
        if analysis['issues']:
            f.write(f"\n### Issues\n")
            for issue in analysis['issues']:
                f.write(f"- {issue}\n")
        
        if analysis['recommendations']:
            f.write(f"\n### Recommendations\n")
            for rec in analysis['recommendations']:
                f.write(f"- {rec}\n")
        
        f.write(f"\n## Per-Run Details\n\n")
        f.write(f"| Run | Ending | Months | Papers | Thesis% | Lowest Morale | Exhaustion |\n")
        f.write(f"|-----|--------|--------|--------|---------|---------------|------------|\n")
        for r in report['per_run_data']:
            f.write(f"| {r['run_number']} | {r['end_reason']} | {r['months_survived']} | "
                   f"{r['papers_published']} | {r['thesis_progress']}% | "
                   f"{r['lowest_morale']} | {r['exhaustion_count']} |\n")
    
    print(f"✅ Markdown summary saved to: {md_file}")


if __name__ == '__main__':
    asyncio.run(main())
