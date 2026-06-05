#!/usr/bin/env python3
import asyncio
import json
from playwright.async_api import async_playwright
from dataclasses import dataclass, asdict
from typing import List

@dataclass
class RunMetrics:
    run_number: int
    ending: str
    total_months: int
    lowest_morale: int
    papers_published: int
    stuck_states: int
    specialization: str
    notes: List[str]

class GradQuestPlaytester:
    def __init__(self):
        self.results: List[RunMetrics] = []
    
    async def play_game(self, run_number: int) -> RunMetrics:
        m = RunMetrics(run_number, "Unknown", 0, 100, 0, 0, "", [])
        specs = ['experimentalist', 'theoretician', 'computational']
        m.specialization = specs[run_number % 3]
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(viewport={'width': 1280, 'height': 800})
            
            await page.goto('file:///Users/guozhenghui/Desktop/WXY/ComBio/GradQuest/docs/index.html')
            await page.wait_for_selector('#start-screen', timeout=10000)
            
            await page.click(f'#spec-{m.specialization}')
            await page.wait_for_timeout(400)
            await page.click('#start-game-btn')
            await page.wait_for_timeout(1000)
            
            for turn in range(300):
                end = await page.query_selector('#end-screen')
                if end and await end.is_visible():
                    txt = await page.text_content('#end-title') or ""
                    m.ending = self._parse_ending(txt)
                    stats = await page.text_content('#end-stats') or ""
                    m.notes.append(stats[:100])
                    break
                
                modal_visible = await page.evaluate('''() => {
                    const m = document.getElementById('event-modal');
                    return m && m.style.display !== 'none';
                }''')
                
                if modal_visible:
                    await page.click('.event-modal-btn')
                    await page.wait_for_timeout(300)
                    continue
                
                state = await page.evaluate('''() => {
                    const b = document.getElementById('morale-bar');
                    const msg = document.getElementById('message-log')?.textContent || '';
                    return {
                        morale: b ? (parseInt(b.style.width) || 50) : 50,
                        papers: parseInt(document.getElementById('papers')?.textContent || '0'),
                        months: parseInt(document.getElementById('total-months')?.textContent || '1'),
                        message: msg,
                    };
                }''')
                
                if state['morale'] < m.lowest_morale:
                    m.lowest_morale = state['morale']
                m.papers_published = state['papers']
                m.total_months = state['months']
                
                msg = state['message']
                quals_urgent = 'QUALS' in msg and ('2 MONTHS' in msg or 'NEXT MONTH' in msg or 'CRITICAL' in msg)
                
                # Priority 1: Critical morale - must recover
                if state['morale'] < 25:
                    await page.evaluate('''() => {
                        const btns = document.querySelectorAll('#actions .action-btn:not(.disabled)');
                        for (const b of btns) {
                            if (b.textContent.includes('Medical Leave')) { b.click(); return; }
                        }
                        for (const b of btns) {
                            if (b.textContent.includes('Time Off')) { b.click(); return; }
                        }
                        for (const b of btns) {
                            if (b.textContent.includes('Break')) { b.click(); return; }
                        }
                    }''')
                # Priority 2: Quals preparation when urgent
                elif quals_urgent and state['morale'] >= 25:
                    await page.evaluate('''() => {
                        const btns = document.querySelectorAll('#actions .action-btn:not(.disabled)');
                        for (const b of btns) {
                            if (b.textContent.includes('Study for Quals')) { b.click(); return; }
                        }
                        for (const b of btns) { b.click(); return; }
                    }''')
                # Priority 3: Normal research
                else:
                    await page.evaluate('''() => {
                        const btns = document.querySelectorAll('#actions .action-btn:not(.disabled)');
                        const priorities = ['Defend Thesis', 'Write Thesis', 'Draft Paper', 'Make Figures',
                                          'Validate Discovery', 'Develop Findings', 'Work on Idea', 'Read Papers',
                                          'Pitch Session'];
                        for (const p of priorities) {
                            for (const b of btns) {
                                if (b.textContent.includes(p)) { b.click(); return; }
                            }
                        }
                        for (const b of btns) { b.click(); return; }
                    }''')
                
                await page.wait_for_timeout(250)
            
            if m.ending == "Unknown":
                m.ending = "Timeout"
            
            await browser.close()
        return m
    
    def _parse_ending(self, text):
        t = (text or "").lower()
        if 'phd' in t or 'doctorate' in t or 'congratulations' in t:
            return 'PhD'
        if 'master' in t:
            return "Master's"
        if 'drop' in t or 'quit' in t or 'game over' in t:
            return 'Dropout'
        if 'time' in t:
            return 'Timeout'
        return 'Unknown'
    
    async def run(self, num_runs=5):
        print(f"Running {num_runs} playtests...")
        print("=" * 60)
        self.results = []
        
        for i in range(1, num_runs + 1):
            print(f"Run {i}: ", end="", flush=True)
            try:
                m = await self.play_game(i)
                self.results.append(m)
                print(f"{m.ending} in {m.total_months}mo (morale: {m.lowest_morale}, papers: {m.papers_published})")
            except Exception as e:
                print(f"ERROR: {str(e)[:50]}")
        
        print("=" * 60)
    
    def report(self):
        if not self.results:
            return "No results"
        
        lines = ["# GradQuest Playtest Report", f"\nRuns: {len(self.results)}", "=" * 60]
        
        endings = {}
        months, morale, papers, stuck = [], [], [], []
        
        for r in self.results:
            endings[r.ending] = endings.get(r.ending, 0) + 1
            months.append(r.total_months)
            morale.append(r.lowest_morale)
            papers.append(r.papers_published)
            stuck.append(r.stuck_states)
        
        lines.append("\n## Endings")
        for e, c in sorted(endings.items(), key=lambda x: -x[1]):
            lines.append(f"- {e}: {c} ({c/len(self.results)*100:.0f}%)")
        
        lines.append(f"\n## Time: avg={sum(months)/len(months):.1f}mo, range={min(months)}-{max(months)}, median={sorted(months)[len(months)//2]}")
        lines.append(f"## Morale: avg_lowest={sum(morale)/len(morale):.1f}, min={min(morale)}")
        lines.append(f"## Papers: avg={sum(papers)/len(papers):.1f}, max={max(papers)}")
        lines.append(f"## Stuck States: {sum(stuck)}")
        
        lines.append("\n## Details")
        for r in self.results:
            lines.append(f"Run {r.run_number}: {r.ending} | {r.total_months}mo | {r.papers_published} papers | morale: {r.lowest_morale} | {r.specialization}")
        
        lines.append("\n" + "=" * 60)
        lines.append("\n## Analysis")
        
        avg_mo = sum(months)/len(months)
        if avg_mo < 50:
            lines.append(f"- ⚠️ Too fast (avg {avg_mo:.1f}mo, target 60-75)")
        elif avg_mo > 85:
            lines.append(f"- ⚠️ Too slow (avg {avg_mo:.1f}mo, target 60-75)")
        else:
            lines.append(f"- ✅ Good pacing (avg {avg_mo:.1f}mo)")
        
        phd = endings.get('PhD', 0)
        completed = len([r for r in self.results if r.ending not in ['Timeout', 'Unknown']])
        if completed > 0:
            rate = phd / completed * 100
            if rate < 30:
                lines.append(f"- ⚠️ Hard (PhD {rate:.0f}%)")
            elif rate > 70:
                lines.append(f"- ⚠️ Easy (PhD {rate:.0f}%)")
            else:
                lines.append(f"- ✅ Balanced (PhD {rate:.0f}%)")
        
        if sum(stuck) > 0:
            lines.append(f"- ⚠️ {sum(stuck)} stuck states")
        
        timeouts = len([r for r in self.results if r.ending == 'Timeout'])
        if timeouts > 0:
            lines.append(f"- ⚠️ {timeouts} timeouts")
        
        return '\n'.join(lines)

async def main():
    t = GradQuestPlaytester()
    await t.run(5)
    r = t.report()
    print("\n" + r)
    
    with open('/Users/guozhenghui/Desktop/WXY/ComBio/GradQuest/playtest_report.md', 'w') as f:
        f.write(r)
    with open('/Users/guozhenghui/Desktop/WXY/ComBio/GradQuest/playtest_data.json', 'w') as f:
        json.dump([asdict(x) for x in t.results], f, indent=2)
    print("\n✓ Saved to playtest_report.md and playtest_data.json")

if __name__ == '__main__':
    asyncio.run(main())
