
// Inject test panel UI
const panel = document.createElement('div');
panel.id = 'test-results-panel';
panel.style.cssText = 'position: fixed; top: 20px; right: 20px; width: 350px; background: #1e293b; border: 1px solid #475569; border-radius: 8px; z-index: 9999; box-shadow: 0 10px 25px rgba(0,0,0,0.5); padding: 15px; color: #f8fafc; font-family: sans-serif;';
panel.innerHTML = `
    <h3 style="margin: 0 0 10px 0; font-size: 1.1rem; border-bottom: 1px solid #475569; padding-bottom: 10px;">🧪 Test Suite</h3>
    <div id="test-summary" style="font-size: 0.9rem; margin-bottom: 15px;">Running tests...</div>
    <div id="test-details" style="display: flex; flex-direction: column; gap: 8px; max-height: 500px; overflow-y: auto;"></div>
`;
document.body.appendChild(panel);


const TestSuite = {
            results: [],

            assert(condition, message) {
                if (!condition) {
                    throw new Error(message || 'Assertion failed');
                }
            },

            async runTest(name, testFn) {
                try {
                    await testFn();
                    this.results.push({ name, status: 'PASS', error: null });
                    return true;
                } catch (error) {
                    this.results.push({ name, status: 'FAIL', error: error.message });
                    return false;
                }
            },

            renderResults() {
                const summaryEl = document.getElementById('test-summary');
                const detailsEl = document.getElementById('test-details');

                const passed = this.results.filter(r => r.status === 'PASS').length;
                const failed = this.results.filter(r => r.status === 'FAIL').length;

                summaryEl.innerHTML = `
                    <span style="color: #4ade80; font-weight: bold;">${passed} PASSED</span> |
                    <span style="color: #ef4444; font-weight: bold;">${failed} FAILED</span> |
                    <span style="color: #94a3b8;">${this.results.length} TOTAL</span>
                `;

                detailsEl.innerHTML = this.results.map(r => `
                    <div style="padding: 10px; border-radius: 8px; background: ${r.status === 'PASS' ? 'rgba(34, 197, 94, 0.1)' : 'rgba(239, 68, 68, 0.1)'}; border-left: 4px solid ${r.status === 'PASS' ? '#22c55e' : '#ef4444'};">
                        <div style="font-weight: 600; color: ${r.status === 'PASS' ? '#22c55e' : '#ef4444'};">
                            ${r.status === 'PASS' ? '✓' : '✗'} ${r.name}
                        </div>
                        ${r.error ? `<div style="color: #f87171; font-size: 0.9rem; margin-top: 4px;">${r.error}</div>` : ''}
                    </div>
                `).join('');
            },

            async runAll() {
                console.log('[TestSuite] Starting tests...');

                // Test 1: Defense Gating Enforced
                await this.runTest('defenseGatingEnforced', () => {
                    // Test Gold Standard path
                    const testStateGold = {
                        thesisProgress: 100,
                        items: { paper: 3 },
                        confPaperCount: 0,
                        qualsPassed: true
                    };
                    const unlockedGold = GRADUATION_CONTRACT.defenseUnlocked(testStateGold);
                    this.assert(unlockedGold, 'Defense should be unlocked for 3 Journals');

                    // Test Hybrid path
                    const testStateHybrid = {
                        thesisProgress: 100,
                        items: { paper: 2 },
                        confPaperCount: 2,
                        qualsPassed: true
                    };
                    const unlockedHybrid = GRADUATION_CONTRACT.defenseUnlocked(testStateHybrid);
                    this.assert(unlockedHybrid, 'Defense should be unlocked for 2 Journals + 2 Conferences');

                    // Test incomplete thesis failure
                    const testStateIncomplete = {
                        thesisProgress: 99,
                        items: { paper: 3 },
                        confPaperCount: 0,
                        qualsPassed: true
                    };
                    const unlockedFail = GRADUATION_CONTRACT.defenseUnlocked(testStateIncomplete);
                    this.assert(!unlockedFail, 'Defense should be locked when thesis < 100%');
                });

                // Test 2: One Modal Per Tick
                await this.runTest('oneModalPerTick', () => {
                    const resolver = new EventResolver(game);
                    resolver.shownThisTurn = 0;

                    // Queue 3 events
                    resolver.enqueue({ id: 'event1', priority: 'Major', message: 'Test 1', owner: 'Test' });
                    resolver.enqueue({ id: 'event2', priority: 'Major', message: 'Test 2', owner: 'Test' });
                    resolver.enqueue({ id: 'event3', priority: 'Major', message: 'Test 3', owner: 'Test' });

                    // Mock state
                    const mockState = { totalMonths: 1, eventLog: [] };
                    resolver.resolveTick(mockState);

                    // Only 1 modal should be shown
                    this.assert(resolver.shownThisTurn === 1, `Expected 1 modal, got ${resolver.shownThisTurn}`);
                });

                // Test 3: No Empty Month Logs
                await this.runTest('noEmptyMonthLogs', () => {
                    game.selectSpecialization('computational');
                    game.start();

                    // Run 12 turns
                    for (let i = 0; i < 12; i++) {
                        game.advanceMonth();
                        game.waitingForAcknowledge = false;
                        if (game.eventResolver) game.eventResolver.resolveTick(game.state);
                    }

                    // Check that eventLog has entries
                    const hasLogs = game.state.eventLog && game.state.eventLog.length > 0;
                    this.assert(hasLogs, 'Event log should not be empty after 12 turns');

                    // Check no empty entries
                    const emptyEntries = game.state.eventLog.filter(e => !e.text || e.text.trim() === '');
                    this.assert(emptyEntries.length === 0, `Found ${emptyEntries.length} empty log entries`);
                });

                // Test 4: Conference No Overlap
                await this.runTest('conferenceNoOverlap', () => {
                    game.selectSpecialization('computational');
                    game.start();

                    // Simulate attending conf1
                    game.state.conferenceAttendedThisYear = true;
                    game.state.lastConferenceMonth = game.state.totalMonths;

                    // Force standard actions mode and clear any active events
                    const originalCriticalMode = game.CONST.CRITICAL_PATH_MODE;
                    game.CONST.CRITICAL_PATH_MODE = false;
                    game.state.eventActive = false;
                    game.waitingForAcknowledge = false;

                    // Check that seek_conference is absent and conf_recovery is present and disabled
                    const actions = game.getActions();
                    console.log('[DEBUG] actions:', actions.map(a => a.id));

                    const seekAction = actions.find(a => a.id === 'seek_conference');
                    const recoveryAction = actions.find(a => a.id === 'conf_recovery');

                    this.assert(seekAction === undefined, 'seek_conference action should NOT be present during cooldown');
                    this.assert(recoveryAction !== undefined, 'conf_recovery action should be present during cooldown');
                    this.assert(recoveryAction.disabled === true, 'conf_recovery action should be disabled');

                    // Restore
                    game.CONST.CRITICAL_PATH_MODE = originalCriticalMode;
                });

                // Test 5: Single Primary Stat Mutation
                await this.runTest('singlePrimaryStatMutation', () => {
                    // Track state mutations
                    let mutationCount = 0;
                    const originalUpdateState = game.updateState;

                    game.updateState = function(changes, owner) {
                        const primaryStats = Object.keys(changes).filter(key =>
                            STATE_CLASSIFICATION.primary.hasOwnProperty(key)
                        );
                        if (primaryStats.length > 1) {
                            mutationCount = primaryStats.length;
                        }
                        return originalUpdateState.call(this, changes, owner);
                    };

                    // Perform an action
                    game.selectSpecialization('computational');
                    game.start();
                    game.doAction('read');

                    // Restore
                    game.updateState = originalUpdateState;

                    this.assert(mutationCount <= 1, `Action mutated ${mutationCount} primary stats, expected <= 1`);
                });

                // Test 6: Defense State Cleanup
                await this.runTest('defenseStateCleanup', () => {
                    game.selectSpecialization('computational');
                    game.start();

                    // Set up defense state
                    game.state.defenseActive = true;
                    game.state.defenseTurn = 2;
                    game.state.defenseThesisQuality = 80;
                    game.state.defensePresentation = 70;
                    game.state.defenseCommittee = 60;
                    game.state.uiMode = 'FINALE';

                    // Call endDefense (simulating completion)
                    game.defenseState = { approval: 100 };
                    game.endDefense();

                    // Check cleanup
                    this.assert(game.state.defenseActive === false, 'defenseActive should be false');
                    this.assert(game.state.defenseTurn === 0, 'defenseTurn should be 0');
                    this.assert(game.state.defenseThesisQuality === 0, 'defenseThesisQuality should be 0');
                    this.assert(game.state.defensePresentation === 0, 'defensePresentation should be 0');
                    this.assert(game.state.defenseCommittee === 0, 'defenseCommittee should be 0');
                    this.assert(game.state.uiMode === 'NORMAL', 'uiMode should be NORMAL');
                });

                // Test 7: Legacy Save Migration
                await this.runTest('legacySaveMigration', () => {
                    const legacySave = {
                        version: '2.57',
                        stress: 150,
                        funding: 12,
                        teachingLoad: true,
                        papers: [{ type: 'journal' }, { type: 'journal' }, { type: 'conference' }],
                        statuses: []
                    };

                    const migrated = game.migrateSave(legacySave);

                    // Version
                    this.assert(migrated.version === GAME_VERSION, `Version should be migrated to ${GAME_VERSION}`);

                    // Stress cap
                    this.assert(migrated.stress === 100, `Stress should be capped at 100, got ${migrated.stress}`);

                    // Funding -> fundingMonths
                    this.assert(migrated.fundingMonths === 12, 'Funding should be migrated to fundingMonths');
                    this.assert(migrated.funding === undefined, 'Legacy funding field should be deleted');

                    // teachingLoad -> teaching_load status
                    this.assert(migrated.statuses.includes('teaching_load'), 'teaching_load status should be added');
                    this.assert(migrated.teachingLoad === undefined, 'Legacy teachingLoad field should be deleted');

                    // Papers
                    this.assert(migrated.items.paper === 2, `Should have 2 journals, got ${migrated.items?.paper}`);
                    this.assert(migrated.confPaperCount === 1, `Should have 1 conference, got ${migrated.confPaperCount}`);
                    this.assert(migrated.papers === undefined, 'Legacy papers array should be deleted');
                });

                // Test 8: EventResolver Queue Semantics
                await this.runTest('eventResolverSemantics', () => {
                    // Ensure eventResolver exists
                    if (!game.eventResolver) game.eventResolver = { queue: [], enqueue: function(){} };
                    // Wait, we can't instantiate it if it's not global. But game.eventResolver is created in startGame.
                    game.selectSpecialization('computational');
                    game.start();
                    const resolver = game.eventResolver;

                    // Clear queue from start messages
                    resolver.eventQueue = [];
                    resolver.processedThisTick.clear();
                    resolver.shownThisTurn = 0;
                    game.waitingForAcknowledge = false;

                    // Enqueue Major and Silent
                    resolver.enqueue({ id: 'modal1', priority: 'Major', message: 'Big problem', owner: 'Test' });
                    resolver.enqueue({ id: 'silent1', priority: 'Silent', message: 'Small log', owner: 'Test' });

                    const mockState = { totalMonths: 1, eventLog: [] };

                    // 1. Resolve Tick: Should render modal, but NOT log silent yet
                    resolver.resolveTick(mockState);

                    this.assert(resolver.shownThisTurn === 1, `Expected 1 modal shown, got ${resolver.shownThisTurn}`);
                    // Since waitingForAcknowledge is true and shownThisTurn > 0, the silent log should be deferred
                    const deferredSilent = resolver.eventQueue.find(e => e.id === 'silent1');
                    this.assert(deferredSilent !== undefined, 'Silent event should be deferred in queue');

                    // Mock DOM for _renderLogMessage to prevent crash if it gets called early
                    const mockLogEl = document.createElement('div');
                    mockLogEl.id = 'message-log';
                    document.body.appendChild(mockLogEl);

                    // Simulate modal clear
                    resolver.shownThisTurn = 0;
                    game.waitingForAcknowledge = false;

                    // 2. Resolve Tick again: Should now log silent
                    resolver.resolveTick(mockState);

                    const resolvedSilent = resolver.eventQueue.find(e => e.id === 'silent1');
                    this.assert(resolvedSilent === undefined, 'Silent event should be removed from queue');
                    const foundInLog = game.state.eventLog.some(e => e.text.includes('Small log') && e.modal === false);
                    this.assert(foundInLog, 'Silent event text should reach eventLog with modal=false');

                    // Cleanup
                    document.body.removeChild(mockLogEl);

                    // Overflow Semantics Test
                    resolver.eventQueue = [];
                    // Fill queue with 50 Silent events
                    for(let i=0; i<50; i++) {
                        resolver.enqueue({ id: `s${i}`, priority: 'Silent', message: 'spam', owner: 'Test' });
                    }
                    // Enqueue 1 Major event (should cause overflow)
                    resolver.enqueue({ id: 'm1', priority: 'Major', message: 'Major event', owner: 'Test' });

                    // Length should be capped at 50, and the Major should STILL exist, while oldest Silent dropped
                    this.assert(resolver.eventQueue.length === 50, `Expected queue length 50, got ${resolver.eventQueue.length}`);
                    const majorEvent = resolver.eventQueue.find(e => e.id === 'm1');
                    this.assert(majorEvent !== undefined, 'Major event should be preserved during overflow');
                    const droppedSilent = resolver.eventQueue.find(e => e.id === 's0');
                    this.assert(droppedSilent === undefined, 'Oldest Silent event (s0) should be dropped');
                });

                // Test 9: Hybrid route guidance and conference-to-journal conversion
                await this.runTest('hybridRouteGuidanceAndConversion', () => {
                    game.selectSpecialization('computational');
                    game.start();
                    game.waitingForAcknowledge = false;
                    if (game.eventResolver) game.eventResolver.eventQueue = [];

                    game.state.qualsPassed = true;
                    game.state.items = { paper: 0, key_discovery: 1, figure: 3 };
                    game.state.confPaperCount = 3;
                    game.state.pendingPapers = [];
                    game.state.thesisProgress = 100;
                    game.syncGraduationState();
                    game.updateGraduationCard();

                    const guidance = game.getHybridGuidance();
                    this.assert(guidance.level === 'warning', 'Conference-heavy hybrid route should show a warning');
                    this.assert(guidance.text.includes('journal'), 'Hybrid warning should name the missing journal requirement');

                    const actions = game.getActions();
                    const expandAction = actions.find(a => a.id === 'expand_conf_journal');
                    this.assert(expandAction !== undefined, 'Conference-heavy route should offer Expand Conf -> Journal');

                    const confAction = actions.find(a => a.id === 'conf_paper');
                    this.assert(confAction && confAction.desc.includes('Conference papers alone cannot unlock defense'), 'Extra conference paper should warn that journals are still required');

                    const previousConfs = game.state.confPaperCount;
                    const previousMorale = game.state.morale;
                    game.doAction('expand_conf_journal');

                    this.assert(game.state.confPaperCount === previousConfs, 'Expansion should not delete existing conference papers');
                    this.assert(game.state.pendingPapers.some(p => p.type === 'conference_extension'), 'Expansion should submit a journal paper for review');
                    this.assert(game.state.morale <= previousMorale - 8, 'Expansion should cost morale');
                });

                // Test 10: Quals onboarding is visible from the first year
                await this.runTest('qualsOnboardingPinned', () => {
                    game.selectSpecialization('computational');
                    game.start();
                    game.waitingForAcknowledge = false;
                    if (game.eventResolver) game.eventResolver.eventQueue = [];

                    const monthsUntilQuals = game.getMonthsUntilQuals(game.state);
                    this.assert(monthsUntilQuals === 12, `Expected 12 months until quals at start, got ${monthsUntilQuals}`);

                    const countdown = game.getQualsCountdown(game.state);
                    this.assert(countdown && countdown.months === 12, 'Quals countdown should appear at 12 months');

                    const actions = game.getActions();
                    this.assert(actions[0].id === 'quals', `Expected pinned quals action first, got ${actions[0]?.id}`);
                    this.assert(actions[0].name.includes('Study for Quals'), 'Pinned quals action should clearly name Study for Quals');
                });

                // Test 11: Critical path surfaces the next concrete research step before more reading
                await this.runTest('criticalPathNextStepOrder', () => {
                    game.selectSpecialization('computational');
                    game.start();
                    game.waitingForAcknowledge = false;
                    if (game.eventResolver) game.eventResolver.eventQueue = [];
                    game.state.qualsPassed = true;

                    game.state.items = { idea: 1 };
                    let actions = game.getActions();
                    this.assert(actions.findIndex(a => a.id === 'work_idea') < actions.findIndex(a => a.id === 'read'), 'Work on Idea should appear before Read when an idea exists');

                    game.state.items = { key_discovery: 1, figure: 3 };
                    actions = game.getActions();
                    this.assert(actions.findIndex(a => a.id === 'write_paper') < actions.findIndex(a => a.id === 'read'), 'Journal submission should appear before Read when figures are ready');
                    this.assert(actions.findIndex(a => a.id === 'write_paper') < actions.findIndex(a => a.id === 'conf_paper'), 'Journal submission should be the guided default before conference paper');

                    game.state.items = { paper: 3 };
                    game.state.thesisProgress = 0;
                    actions = game.getActions();
                    this.assert(actions.findIndex(a => a.id === 'write_thesis') < actions.findIndex(a => a.id === 'read'), 'Write Thesis should appear before Read once portfolio is ready');

                    game.state.thesisProgress = 100;
                    game.state.defensePrepared = false;
                    actions = game.getActions();
                    this.assert(actions[0].id === 'prepare_defense', `Expected Prepare Defense first when ready, got ${actions[0]?.id}`);
                });

                // Test 12: Defense strain affects skepticism and track penalties
                await this.runTest('defenseStrainAffectsSkepticism', () => {
                    game.selectSpecialization('computational');
                    game.start();
                    game.waitingForAcknowledge = false;
                    if (game.eventResolver) game.eventResolver.eventQueue = [];

                    game.state.items = { paper: 3 };
                    game.state.confPaperCount = 0;
                    game.state.thesisProgress = 100;
                    game.state.qualsPassed = true;
                    game.state.strategicAlignment = 60;
                    game.state.peerNetwork = 20;

                    game.state.morale = 80;
                    game.state.stress = 0;
                    game.state.telemetry.moraleLowMonths = 0;
                    game.state.statuses = new Set();
                    const healthy = game.evaluateDefenseCriteria();

                    game.state.morale = 18;
                    game.state.stress = 85;
                    game.state.telemetry.moraleLowMonths = 6;
                    game.state.statuses = new Set(['exhaustion']);
                    const strained = game.evaluateDefenseCriteria();
                    const strain = game.getDefenseStrain(game.state);

                    this.assert(strained.skepticismMultiplier > healthy.skepticismMultiplier, 'Strained defense should increase skepticism');
                    this.assert(strain.presentationPenalty > 0, 'Strained defense should penalize presentation');
                    this.assert(strained.breakdown.some(t => t.includes('Low Morale')), 'Defense breakdown should mention low morale');
                    this.assert(strained.breakdown.some(t => t.includes('Stress')), 'Defense breakdown should mention stress');
                });

                this.renderResults();
                console.log('[TestSuite] Tests complete:', this.results);

                return this.results;
            }
        };

        // Run tests after game loads
        document.addEventListener('DOMContentLoaded', () => {
            setTimeout(() => TestSuite.runAll(), 500);
        });
