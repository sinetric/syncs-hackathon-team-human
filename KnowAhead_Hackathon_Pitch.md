# Know Ahead

> **Know what's changing around your life before it affects you.**

## 1. Overview

**Know Ahead** is a personal urban intelligence system that continuously monitors changes around the places that matter to a user and translates fragmented city data into personalised, actionable insight.

Sydney is constantly changing:

- Construction and development
- Roadworks and infrastructure
- Weather
- Flooding
- Events
- Emergencies
- Planning and development approvals

The information already exists, but it is scattered across many different sources. People often discover a change only after it has already affected them.

Know Ahead brings these signals together and answers three questions:

> **What's changing? → Will it affect me? → What should I do?**

---

# 2. The Problem

Sydney residents are surrounded by constantly changing urban conditions, but there is no single system that connects those changes to their personal circumstances.

A development approval may exist on a planning portal.

A road closure may be published by a transport authority.

A weather warning may exist in a weather service.

An event may be listed separately.

A resident is expected to discover, interpret, and connect all of this information themselves.

### The fundamental problem

**People don't know what they don't know.**

A person may not think to search:

- "Are there developments near my home?"
- "Is a major construction project starting next month?"
- "Will this road project affect my commute?"
- "Is there something nearby that could affect my lease decision?"

The information exists, but the user does not know they need to look for it.

---

# 3. The Solution

Know Ahead allows users to save locations that matter to them:

- 🏠 Home
- 💼 Work
- 🏫 School
- 📍 Places they are considering moving to
- 🏪 Potential business locations
- Other important locations

Know Ahead continuously monitors relevant urban signals around those locations.

Instead of simply displaying raw information, it transforms the information into a personalised interpretation:

```text
Urban Data
    ↓
Change Detection
    ↓
Geospatial Relevance
    ↓
Impact Analysis
    ↓
Personalisation
    ↓
Prediction
    ↓
Action
```

The system doesn't just ask:

> "What is happening?"

It asks:

> **"What does this mean for this person?"**

---

# 4. What Makes Know Ahead Different?

## Existing apps

Most existing systems follow a model similar to:

```text
Data → Alert
```

Examples:

- Google Maps → navigation and traffic
- Opal → public transport information
- Weather apps → weather
- Council websites → individual planning and construction information
- Event platforms → events

Each system provides a useful but narrow view.

## Know Ahead

Know Ahead connects these pieces:

```text
Data
 ↓
Change Detection
 ↓
Impact
 ↓
Personalisation
 ↓
Prediction
 ↓
Action
```

### Core differentiation

> **We don't predict the incident. We predict the impact.**

A development approval is not necessarily useful by itself.

Knowing that the development is:

- 180m from your home
- expected to involve construction
- active during your lease period
- likely to affect traffic and noise

is much more useful.

Know Ahead connects the event to the user's circumstances.

---

# 5. The Two Core Experiences

## A. Proactive Monitoring — "What Changed?"

Know Ahead continuously watches the user's saved locations.

Example:

### Yesterday

🟢 No major changes.

### Today

🚨 **New development approval detected 180m from your home.**

Know Ahead analyses the event and determines:

- What changed
- How close it is
- What type of change it is
- How long it may last
- Potential effects
- Whether the effect overlaps with the user's circumstances

The user receives an explanation rather than being expected to discover and interpret the source themselves.

### Key insight

> **AI can answer questions when you ask. Know Ahead watches for the questions you didn't know you needed to ask.**

---

# 6. Decision Support — "Before You Commit"

Know Ahead can help users make decisions about locations.

Example:

A user enters an address and asks:

> **"Should I renew my lease?"**

Know Ahead discovers:

- 🏗️ Development — 200m away
- 🚧 Road project — 600m away
- 🌳 New park — 800m away

It then evaluates potential effects:

| Factor | Potential Impact |
|---|---|
| Noise | 🔴 High |
| Traffic | 🟠 Medium |
| Dust | 🟡 Medium |
| Duration | 18 months |

Know Ahead could respond:

> **This construction is likely to overlap with your next lease. Investigate construction hours before renewing.**

The system can turn fragmented urban information into something relevant to a real decision.

---

# 7. Potential Use Cases

## 🏠 Renting / Buying

Before signing a lease or purchasing a property, users can understand what may change around the location.

Questions:

- Is major construction coming?
- Are there planned roadworks?
- Are there developments nearby?
- Could construction overlap with my lease?
- Is the neighbourhood changing?

## 👨‍👩‍👧 Choosing Where to Live

Compare potential locations based on their expected future environment.

A property that looks attractive today may have major construction planned nearby.

Know Ahead helps reveal the difference between:

> **What this location is like today**

and

> **What this location may be like during the period I live there.**

## 💻 Working From Home

Users can identify changes that may affect their working environment:

- Construction
- Roadworks
- Events
- Weather
- Noise-producing activity

## 🏪 Choosing a Business Location

Businesses can evaluate potential locations based on upcoming urban changes.

Potential signals:

- Construction
- Road access
- Infrastructure
- New developments
- Events
- Pedestrian or traffic changes

## 🌧️ Planning Your Day

Know Ahead can combine current and upcoming conditions around important locations.

For example:

- Weather
- Flooding
- Road disruptions
- Events
- Transport-related changes

The goal is to provide context rather than simply another alert.

---

# 8. The Product Philosophy

Know Ahead is built around a simple principle:

> **People don't need more data. They need more context.**

Raw information is abundant.

The difficult part is connecting:

**What happened → Where it happened → When it happens → How significant it is → Who it affects → What they should consider doing.**

Know Ahead acts as the intelligence layer between public data and the individual.

---

# 9. System Architecture

A strong MVP architecture should separate deterministic data processing from AI interpretation.

```text
                PUBLIC DATA SOURCES
                        │
        ┌───────────────┼────────────────┐
        ↓               ↓                ↓
   Planning        Infrastructure     Weather
        │               │                │
        └───────────────┼────────────────┘
                        ↓
                DATA NORMALISATION
                        ↓
                GEOSPATIAL FILTERING
                        ↓
                 CHANGE DETECTION
                        ↓
                SIGNAL AGGREGATION
                        ↓
                  IMPACT MODEL
                        ↓
                       LLM
                        ↓
             PERSONALISED EXPLANATION
                        ↓
              RECOMMENDATION / ALERT
```

## Why this architecture?

The AI should not be responsible for determining basic facts that can be established programmatically.

For example:

- Distance from an address → deterministic
- Event coordinates → data source
- Date of an approval → data source
- Change between yesterday and today → change detection
- Duration → source data where available

The LLM can then reason over verified signals.

For example:

> "Given these events, their locations, timing, duration, and the user's stated situation, explain the likely implications in plain English."

This makes the system more reliable and easier to demonstrate.

---

# 10. Data Pipeline

## Step 1 — Collect Data

Potential data categories:

1. Planning / developments
2. Construction / infrastructure
3. Roads
4. Weather
5. Events

For a 24-hour hackathon MVP, focus on **3–5 sources**, rather than attempting to integrate everything.

---

## Step 2 — Normalise

Convert different sources into a common event representation.

Conceptually:

```text
UrbanEvent
├── id
├── type
├── title
├── description
├── latitude
├── longitude
├── start_date
├── end_date
├── source
├── status
└── last_updated
```

This allows different government and public datasets to be analysed consistently.

---

# 11. Change Detection

The core system should compare the current state against previously observed data.

For example:

```text
Previous snapshot
    ↓
No development at location X

Current snapshot
    ↓
Development approval at location X

    ↓

CHANGE DETECTED
```

Possible change types:

- New event
- Updated event
- Event cancelled
- Date changed
- Location changed
- Status changed
- Construction started
- Construction completed

This is what turns Know Ahead from a static information aggregator into a monitoring system.

---

# 12. Geospatial Intelligence

Once an event is detected, Know Ahead determines its relevance to the user's saved locations.

For example:

```text
User Home
     ●
     │
     │ 180m
     │
     ▼
Development
     ▲
     │
     │ 600m
     │
Road Project
```

Distance is an important first-order signal.

But distance alone should not determine impact.

Other factors can include:

- Event type
- Duration
- Scale
- Location
- Road proximity
- Timing
- Construction status
- User context
- Whether the event overlaps with a relevant period

---

# 13. Impact Analysis

A useful conceptual model is:

```text
Impact =
    Event Severity
    × Proximity
    × Duration
    × Exposure
    × User Relevance
```

The exact MVP implementation can be much simpler.

For example:

### Development

Potential impacts:

- Noise
- Dust
- Traffic
- Visual change
- Access disruption
- Construction duration

### Roadworks

Potential impacts:

- Travel time
- Road access
- Parking
- Traffic congestion
- Route changes

### Weather / flooding

Potential impacts:

- Travel
- Outdoor activities
- Accessibility
- Safety
- Event disruption

### Events

Potential impacts:

- Traffic
- Parking
- Noise
- Pedestrian congestion
- Accessibility

The output should not pretend to be an exact scientific prediction.

It should communicate **potential impact and confidence** based on available evidence.

---

# 14. Personalisation

The same urban event can have very different consequences for different people.

For example:

### Person A

Works from home.

A construction project 150m away could be highly relevant because of noise.

### Person B

Works in an office and leaves home at 7:30 AM.

The same construction may have less impact, while a road project on their commute could matter much more.

### Person C

Is considering signing a 12-month lease.

A development expected to last 18 months becomes highly relevant.

Therefore:

```text
Same Event
    ↓
Different User Context
    ↓
Different Impact
    ↓
Different Recommendation
```

This is one of the central reasons Know Ahead is more than an alert system.

---

# 15. Prediction

Know Ahead does not need to predict exactly what incident will happen.

Instead:

> **It predicts how known or detected changes may affect the user.**

For example:

```text
Known development
      +
180m from home
      +
18-month construction period
      +
lease expires in 2 months
      ↓
Potential overlap with user's next lease
      ↓
High relevance
```

This is a much more defensible form of prediction than claiming to predict unforeseen incidents.

---

# 16. Recommendations

The final output should be actionable.

Bad:

> "There is a construction project 200m away."

Better:

> "A construction project is planned approximately 200m from your home and may overlap with your next lease."

Best:

> "This construction is likely to overlap with your next lease. Investigate permitted construction hours and expected noise before renewing."

The recommendation should be:

- Clear
- Personalised
- Evidence-based
- Appropriately cautious

Know Ahead should help users make decisions, not make decisions for them.

---

# 17. Proactive Alerts

The alert should communicate the complete chain:

```text
🚨 WHAT CHANGED?
New development approval

📍 WHERE?
180m from your home

📅 WHEN?
Detected today
Construction expected to continue for ~18 months

⚠️ POTENTIAL IMPACT
Noise: High
Traffic: Medium
Dust: Medium

💡 WHY IT MATTERS
This overlaps with your next lease period.

👉 WHAT TO CONSIDER
Investigate construction hours before renewing.
```

This is substantially more useful than:

> "New development nearby."

---

# 18. 24-Hour Hackathon MVP

Do **not** try to build the entire vision.

Build one impressive end-to-end flow.

## MVP Flow

```text
User enters address
        ↓
Collect Sydney signals
        ↓
Detect changes
        ↓
Calculate distance
        ↓
Determine potential impact
        ↓
AI explains impact
        ↓
Personalised recommendation
        ↓
Proactive alert
```

## Recommended scope

Focus on approximately **3–5 data sources**:

- Planning / developments
- Construction / infrastructure
- Roads
- Weather
- Events

The best MVP is one where the entire pipeline actually works.

---

# 19. Recommended Demo

The strongest demo should create a moment where the user discovers something they did not know.

## Demo scenario

### Step 1

User enters their home address.

### Step 2

Know Ahead scans nearby signals.

### Step 3

The system detects a recently changed planning or development record.

### Step 4

The UI displays:

> 🚨 **Something changed 180m from your home.**

### Step 5

A map shows:

- User's location
- Development
- Other nearby relevant signals

### Step 6

Know Ahead explains:

> "A development approval was detected yesterday approximately 180m from your home."

### Step 7

The system analyses potential effects:

| Impact | Rating |
|---|---|
| Noise | 🔴 High |
| Traffic | 🟠 Medium |
| Dust | 🟡 Medium |

### Step 8

The user asks:

> "Should I renew my lease?"

### Step 9

Know Ahead responds:

> "This construction is likely to overlap with your next lease. Investigate construction hours before renewing."

### Step 10

Finish with:

> **"You didn't know you needed to ask."**

That is the core magic moment.

---

# 20. UI / Front-End Concept

A strong MVP interface could contain:

## Dashboard

### My Locations

```text
🏠 Home
   Sydney, NSW

💼 Work
   Sydney, NSW

🏫 University
   Sydney, NSW
```

### Pulse

```text
🚨 1 new change near Home

🏗️ Development approval
180m away
Detected today

Potential impact:
Noise     🔴 High
Traffic   🟠 Medium
Dust      🟡 Medium
```

### Map

Show the user's saved locations alongside relevant events.

### Event Details

Display:

- What changed
- Source
- Date detected
- Distance
- Duration
- Potential impacts
- Confidence
- Recommendation

### Decision Mode

A user can ask:

> "Should I renew my lease?"

or:

> "Would you live here?"

The system then analyses the surrounding signals.

---

# 21. What the AI Should Do

The AI is best used as an interpretation and reasoning layer.

It can:

- Summarise complex source information
- Connect multiple signals
- Explain potential impacts
- Personalise information
- Answer natural-language questions
- Generate recommendations
- Explain uncertainty

The AI should receive structured, verified context rather than being expected to hallucinate the underlying facts.

Conceptually:

```text
Structured Events
+
User Location
+
User Context
+
Time Horizon
        ↓
       LLM
        ↓
Explanation
+
Potential Impact
+
Recommendation
```

---

# 22. What the Algorithm Should Do

Deterministic systems should handle:

- Data ingestion
- Data normalisation
- Deduplication
- Change detection
- Geospatial calculations
- Distance calculations
- Time-window calculations
- Event classification
- Basic impact scoring
- Confidence / evidence tracking

This creates a strong division:

> **Code establishes the facts. AI explains their implications.**

---

# 23. Important Product Principle: Evidence

Every recommendation should ideally be traceable back to underlying signals.

For example:

```text
Recommendation
"Investigate construction hours before renewing."

        ↑

Reasoning
"Potentially high noise impact"

        ↑

Evidence
Development 180m away
Construction duration: 18 months
Construction-related activity
Lease period overlap
```

This makes Know Ahead more trustworthy.

---

# 24. Trust and Uncertainty

Know Ahead should distinguish between:

### Known

> "A development approval was recorded."

### Inferred

> "The development may increase local traffic."

### Predicted

> "This may overlap with your lease period."

The system should avoid presenting uncertain predictions as guaranteed outcomes.

A good product can say:

> **Potential impact: High**

without claiming:

> **This will definitely cause high noise.**

---

# 25. Competitive Positioning

Know Ahead is not trying to replace:

- Google Maps
- Opal
- Weather applications
- Council websites
- Planning portals
- Event platforms

Instead, it sits **above them** as a personal intelligence layer.

```text
                 Know Ahead
                      │
          ┌───────────┼───────────┐
          ↓           ↓           ↓
      Planning      Roads      Weather
          ↓           ↓           ↓
      Construction  Events   Infrastructure
          └───────────┼───────────┘
                      ↓
               Personal Context
                      ↓
                User Decisions
```

The product's value comes from **connecting the signals**.

---

# 26. Strongest Messaging

## One-liner

> **Know Ahead tells you what's changing around the places that matter to you — and what those changes mean for your life.**

## Shorter tagline

> **See what's coming. Understand the impact. Make better decisions.**

## Differentiator

> **We don't just detect events. We detect changes, connect them to your life, and explain what you should consider doing.**

## Core insight

> **AI answers questions. Know Ahead watches for the questions you didn't know you needed to ask.**

---

# 27. 30-Second Pitch

> **"Sydney is constantly changing, but people only see a snapshot of today. A development gets approved, construction begins, roads change, weather hits and events reshape neighbourhoods — but that information is scattered everywhere.**
>
> **Know Ahead continuously watches the places that matter to you, detects what's changing, connects the signals, predicts the potential impact on your life, and tells you what you should consider doing.**
>
> **It could warn you about something affecting your day, or tell you about construction that could affect your home for the next 18 months.**
>
> **AI answers questions. Know Ahead watches for the questions you didn't know you needed to ask.**
>
> **We don't just tell you what's happening in Sydney. We tell you what it means for your life."**

### Final line

> **Know Ahead — See what's coming. Understand the impact. Make better decisions.**

---

# 28. Expanded Pitch

Sydney is constantly changing.

A development gets approved.

Construction begins.

A road closes.

A new infrastructure project starts.

Severe weather hits.

An event transforms a neighbourhood.

The information already exists, but it is scattered across planning portals, council websites, transport systems, weather services, event platforms and other sources.

People usually discover these changes only after they affect them.

**Know Ahead changes that.**

Users save the places that matter to them — home, work, school, or somewhere they are considering moving to.

Know Ahead continuously monitors what is changing around those locations.

It detects new signals, measures their proximity, connects related events, analyses potential impacts and translates everything into personalised recommendations.

Instead of:

> "Development application approved 180m away."

Know Ahead says:

> "A development was approved 180m from your home. Construction is expected to continue for approximately 18 months and may create significant noise and moderate traffic disruption. This overlaps with your next lease period. Investigate construction hours before renewing."

That's the difference.

**We don't just tell you what's happening. We tell you why it matters.**

And the most important part is that users don't need to know what to search for.

**AI can answer questions when you ask. Know Ahead watches for the questions you didn't know you needed to ask.**

---

# 29. The "Aha" Moment

The entire product can be reduced to one user reaction:

> **"Wait — I didn't know that was happening."**

That is the moment the product should create.

The system's job is to surface information that is:

1. New
2. Nearby
3. Relevant
4. Potentially impactful
5. Actionable

This is the fundamental value proposition.

---

# 30. Hackathon Strategy

For a 24-hour competition, prioritise:

### 1. One polished user journey

Do not build ten incomplete features.

### 2. Real data

Use real Sydney data where possible.

### 3. Real change detection

Demonstrate that the system can identify something newly changed.

### 4. Strong visualisation

Show the event on a map relative to the user's location.

### 5. Personalisation

Give the AI enough user context to make the result feel genuinely personal.

### 6. Explainability

Show:

- What changed
- Where
- When
- Why it matters
- What the system recommends

### 7. The proactive moment

The strongest demo is an alert the user did not explicitly request.

---

# 31. What NOT to Build

Avoid spending the hackathon on:

- Supporting every Sydney data source
- Building a perfect long-term prediction model
- Complex user account systems
- Fully autonomous browsing
- Massive infrastructure
- Overly sophisticated machine learning
- Dozens of notification types
- Perfect property-market predictions

The hackathon goal is not to prove that every possible urban signal can be handled.

The goal is to prove:

> **Fragmented city data can be transformed into proactive, personalised urban intelligence.**

---

# 32. Ideal End-to-End Example

```text
USER
"Monitor my home."

             ↓

Know Ahead
Collect nearby signals

             ↓

CHANGE DETECTION
New development approval detected

             ↓

GEOSPATIAL ANALYSIS
180m from user's home

             ↓

CONTEXT
User is considering renewing a lease

             ↓

IMPACT ANALYSIS
Noise: High
Traffic: Medium
Dust: Medium
Duration: ~18 months

             ↓

AI INTERPRETATION

"This construction is likely to overlap
with your next lease."

             ↓

ACTION

"Investigate construction hours
before renewing."

             ↓

PROACTIVE ALERT

🚨 Something changed near your home.
```

---

# 33. Product North Star

The long-term vision is not simply to become another Sydney information dashboard.

The goal is to build a **personal urban intelligence system**.

A system that understands:

- Where you spend time
- What is changing around you
- When those changes will happen
- Which changes matter to you
- How different signals interact
- What you should consider doing

The ultimate abstraction is:

> **The city changes continuously. Know Ahead keeps you ahead of the change.**

---

# 34. Final Pitch Summary

### Problem

Sydney changes constantly, but information about those changes is fragmented. People often learn about changes only after they affect them.

### Solution

Know Ahead continuously monitors locations important to users, detects changes, connects signals, analyses potential impact and provides personalised recommendations.

### Differentiation

Existing systems primarily provide data or alerts.

Know Ahead provides:

> **Data → Change Detection → Impact → Personalisation → Prediction → Action**

### Killer Feature

**Proactive awareness.**

Know Ahead identifies changes the user did not know they needed to ask about.

### Killer Demo

A user enters their home, Know Ahead detects a new nearby development, analyses its potential impact, connects it to the user's lease decision and recommends an action.

### Killer Line

> **"AI answers questions. Know Ahead watches for the questions you didn't know you needed to ask."**

### Final tagline

> # Know Ahead
> **See what's coming. Understand the impact. Make better decisions.**
