# GradQuest V2.27 QA Testing Log

## Version Verification
- **Confirmed Version**: V2.27 (visible in header)
- **Initial State**: Welcome screen with three specializations: Experimentalist, Theoretician, Computational.

## Test Plan Execution

### Run 1: "Safe" Run (Theoretician)
- **Strategy**: Focus on high morale, steady progress, and early Quals prep. Avoid risky actions like high-throughput experiments.
- **Specialization**: Theoretician (✨ Conceptual Breakthrough, ⚠️ Abstract results).

### Run 2: "Risky" Run (Experimentalist)
- **Strategy**: Aggressive paper submissions, high-risk experiments, and pushing morale to the limit.
- **Specialization**: Experimentalist (✨ Protocol Reuse, ⚠️ Equipment-dependent).

### Run 3: "Edge Case" Run (Computational)
- **Strategy**: Test specific field mechanics, try to trigger "soft locks" or unusual states.
- **Specialization**: Computational (✨ Pipeline Automation, ⚠️ Server-dependent).

### Run 1 Results: "Safe" Run (Theoretician)
- **Outcome**: **LOSS** (Game Over)
- **Stats**:
  - Months elapsed: 33
  - Publications: 0
  - Final morale: 0%
  - Peer Network: 10
  - Strategic Alignment: 0
  - Advisor Happiness: 0%
- **Observations**:
  - Even with a "safe" strategy (prioritizing breaks and quals prep), the morale decay and negative events were overwhelming.
  - 33 months without a single publication suggests the research pipeline might be too slow or the RNG for "Develop Findings" is very punishing for Theoreticians.
  - The "Exhaustion" mechanic seems to trigger very easily and is hard to clear with just "Take a Break".
- **UX Note**: The "Game Over" screen is clear, but the journey to it felt like a slow, unavoidable decline.

### Run 2 Results: "Risky" Run (Experimentalist)
- **Outcome**: **LOSS** (Dismissed after failing quals twice)
- **Stats**:
  - Months elapsed: 16
  - Publications: 0
  - Final morale: 17%
  - Peer Network: 2
  - Strategic Alignment: 2
  - Advisor Happiness: 38%
- **Observations**:
  - The "Risky" strategy of ignoring Quals prep led to a much faster loss (16 months vs 33 months).
  - Failing Quals twice is a hard fail condition that is very effective at ending the game.
  - Experimentalist specialization introduces "Broken Equipment" which blocks research, adding another layer of resource management (time/morale for repairs).
  - Even with aggressive research actions, 0 publications were achieved in 16 months, highlighting the significant time investment required for each paper.

### Run 3 Results: "Edge Case" Run (Computational)
- **Outcome**: **LOSS** (Dismissed after failing quals twice)
- **Stats**:
  - Months elapsed: 16
  - Publications: 0
  - Final morale: 10%
  - Peer Network: 30
  - Strategic Alignment: 0
  - Advisor Happiness: 41%
- **Observations**:
  - The "Pre-allocate Compute" action successfully reduced morale by 5 but provided a "Server stable" status effect, which is a clear field-specific mechanic.
  - Like the risky run, failing to prioritize Quals prep led to a quick dismissal at month 16.
  - The "Conference" action is a good way to build "Peer Network" but doesn't directly advance the research pipeline, creating a strategic tradeoff.
  - **Bug Hunting**: No hard soft-locks were found, but the "Exhaustion" status effect seems to have a very high chance of appearing after any research action when morale is below 50%, which might be too punishing.
  - **Text Rendering**: All text rendered correctly across different screens and modals.
