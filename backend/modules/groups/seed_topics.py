"""
Seed the group_topics table from sud-groups.md.
Called once at startup; idempotent — will not re-seed if seeded topics already exist.
"""
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# Each topic maps directly from the 50 topics in sud-groups.md.
# category choices: Addiction Education | Relapse Prevention | Coping Skills |
#                   Mental Health | Relationships | Emotional Skills |
#                   Identity & Recovery | Practical Life Skills
SEEDED_TOPICS: List[Dict[str, Any]] = [
    {
        "title": "Understanding Addiction as a Disease",
        "category": "Addiction Education",
        "description": (
            "Introduces addiction as a chronic brain-based disorder rather than a moral failing, "
            "and what this means for treatment and recovery."
        ),
        "key_points": [
            "Define addiction and the disease model",
            "Biology, psychology, and environment interactions",
            "What 'chronic, relapsing' means for expectations of recovery",
        ],
        "discussion_questions": [
            "How does thinking of addiction as a disease change how you see yourself?",
            "What messages about addiction did you grow up with?",
            "How does the disease model affect shame and blame?",
        ],
        "activity": "Group brainstorm: list three things addiction is NOT (common myths) and replace each with a fact.",
        "writing_prompt": "Write about one belief you held about addiction that has changed since starting treatment.",
        "facilitator_tips": (
            "Normalize ambivalence. Some members may resist the disease label — validate this "
            "and focus on what the model does to reduce blame. Watch for shame spirals."
        ),
    },
    {
        "title": "How Drugs and Alcohol Affect the Brain and Body",
        "category": "Addiction Education",
        "description": (
            "Explains the neurobiology of substances — reward pathways, tolerance, withdrawal — "
            "and physical health impacts to build insight and motivation."
        ),
        "key_points": [
            "Brain reward system and dopamine",
            "Tolerance, dependence, and withdrawal",
            "Long-term health consequences and benefits of abstinence",
        ],
        "discussion_questions": [
            "What surprised you most about how substances affect the brain?",
            "How has your body changed — for better or worse — since you stopped using?",
            "What does knowing about dopamine change about how you think about cravings?",
        ],
        "activity": "Draw or label a simple brain diagram highlighting the reward pathway. Discuss what happens at each stage of use.",
        "writing_prompt": "Describe one physical change you have noticed in yourself since you stopped using.",
        "facilitator_tips": "Keep the neuroscience accessible — use plain language. Avoid shaming language around physical effects.",
    },
    {
        "title": "The Cycle of Addiction",
        "category": "Addiction Education",
        "description": (
            "Covers the progression from experimental use to dependency and the repeating "
            "binge-crash-resolve-relapse cycle."
        ),
        "key_points": [
            "Stages of use and escalation",
            "How the cycle keeps people stuck",
            "Identifying where you are in the cycle today",
        ],
        "discussion_questions": [
            "Where in the cycle did you feel most stuck?",
            "What kept you going back even when you wanted to stop?",
            "What broke the cycle — even temporarily — for you?",
        ],
        "activity": "Each member draws their personal addiction timeline, noting highs, lows, and turning points.",
        "writing_prompt": "Describe the moment you first recognized you were in a cycle and what that felt like.",
        "facilitator_tips": "Validate that the cycle is not a character flaw. Normalizing the pattern reduces shame and opens the door to change.",
    },
    {
        "title": "Stages of Change and Motivation for Recovery",
        "category": "Addiction Education",
        "description": (
            "Uses the stages-of-change framework to normalize ambivalence and support movement toward change."
        ),
        "key_points": [
            "Overview of stages of change (precontemplation through maintenance)",
            "Normalizing mixed feelings about sobriety",
            "Ways to strengthen motivation and 'decisional balance'",
        ],
        "discussion_questions": [
            "Which stage best describes where you are today?",
            "What are the pros and cons of changing for you?",
            "What has helped you move from one stage to the next?",
        ],
        "activity": "Decisional balance worksheet: list pros and cons of using vs. not using.",
        "writing_prompt": "Write a letter to yourself from the future — what do you want to tell yourself about this moment?",
        "facilitator_tips": "Do not push members to a stage they are not in. Meet ambivalence with curiosity, not confrontation.",
    },
    {
        "title": "Impact of Addiction on Relationships and Family Systems",
        "category": "Relationships",
        "description": (
            "Explores how substance use affects trust, communication, roles, and boundaries within families."
        ),
        "key_points": [
            "Common roles in families affected by SUD",
            "Trust, secrecy, and communication breakdowns",
            "Healthy steps toward repair and accountability",
        ],
        "discussion_questions": [
            "What role did you play in your family during active addiction?",
            "How has your use affected someone you love?",
            "What would it take to begin repairing one relationship?",
        ],
        "activity": "Family roles role-play: identify 'the hero,' 'the scapegoat,' 'the lost child,' 'the mascot,' and discuss.",
        "writing_prompt": "Write about a relationship that was affected by your use and what you hope for it now.",
        "facilitator_tips": "Watch for grief responses. Family wounds are deep. Validate without assigning blame.",
    },
    {
        "title": "Co-Occurring Disorders: When Mental Health and SUD Overlap",
        "category": "Mental Health",
        "description": (
            "Explains how depression, anxiety, PTSD, and other conditions interact with substance use "
            "and why integrated treatment matters."
        ),
        "key_points": [
            "What 'co-occurring' means",
            "How mental health symptoms can trigger use and vice versa",
            "Benefits of coordinated care and honest symptom reporting",
        ],
        "discussion_questions": [
            "Have you ever used substances to manage a mental health symptom?",
            "What came first for you — mental health struggles or substance use?",
            "How does knowing about co-occurring disorders change your treatment goals?",
        ],
        "activity": "Venn diagram: draw two overlapping circles — mental health symptoms and substance use. What goes in the overlap?",
        "writing_prompt": "Describe how your mental health and your use have been connected.",
        "facilitator_tips": "Normalize dual diagnosis. Many members carry shame about psychiatric symptoms — reduce stigma explicitly.",
    },
    {
        "title": "Understanding Cravings and Triggers",
        "category": "Relapse Prevention",
        "description": (
            "Defines internal and external triggers, explains cravings as time-limited experiences, "
            "and prepares members for coping skills groups."
        ),
        "key_points": [
            "Types of triggers (people, places, things, feelings, thoughts)",
            "How cravings show up in the body and mind",
            "Why 'white-knuckling' alone is not enough",
        ],
        "discussion_questions": [
            "What are your top three triggers right now?",
            "Where do you feel cravings in your body?",
            "What is the difference between a craving and a decision to use?",
        ],
        "activity": "Personal trigger map: each member draws and labels their top people, places, feelings, and thoughts that trigger use.",
        "writing_prompt": "Describe a recent craving — what triggered it, how it felt, and how it passed.",
        "facilitator_tips": "Remind the group that cravings peak and pass. Use the 'wave' metaphor — surf it, don't fight it.",
    },
    {
        "title": "Shame, Guilt, and Stigma in Addiction",
        "category": "Emotional Skills",
        "description": (
            "Differentiates shame from guilt, examines internalized stigma, and connects "
            "self-compassion to sustainable recovery."
        ),
        "key_points": [
            "Shame vs guilt and how each shows up",
            "Impact of stigma from others and self-stigma",
            "Self-compassion as an alternative to self-attack",
        ],
        "discussion_questions": [
            "What is one message you received about yourself because of your use?",
            "What is the difference between 'I did a bad thing' and 'I am bad'?",
            "How does shame affect your recovery?",
        ],
        "activity": "Write one shame-based thought on a card. Flip it over and write a compassionate response.",
        "writing_prompt": "Write yourself a letter of compassion for one thing you feel ashamed of.",
        "facilitator_tips": "Go slowly. Shame work is vulnerable. Model self-compassion explicitly in your facilitation tone.",
    },
    {
        "title": "Making Sense of Your Use History",
        "category": "Addiction Education",
        "description": (
            "Helps participants organize their substance use history into a coherent narrative "
            "to increase insight and identify patterns."
        ),
        "key_points": [
            "First use, progression, 'bottoms,' and turning points",
            "Patterns in people/places/feelings surrounding use",
            "Lessons learned and themes you want to change",
        ],
        "discussion_questions": [
            "What do you see when you look at your use history as a whole?",
            "What patterns kept showing up?",
            "What do you want your next chapter to look like?",
        ],
        "activity": "Use history timeline: mark first use, escalation, consequences, attempts to stop, and current moment.",
        "writing_prompt": "Summarize your use history in a paragraph — what is the story you have been living?",
        "facilitator_tips": "Frame history as data, not a verdict. The goal is insight, not re-traumatization.",
    },
    {
        "title": "Addiction, Legal Issues, and Consequences",
        "category": "Addiction Education",
        "description": (
            "Reviews legal, occupational, and financial consequences of substance use and "
            "connects accountability to recovery planning."
        ),
        "key_points": [
            "Common legal and work-related impacts of SUD",
            "Short-term vs long-term consequences",
            "Steps toward legal, financial, and relational repair",
        ],
        "discussion_questions": [
            "How has addiction affected your legal or financial life?",
            "What is one consequence you are still working through?",
            "What would it mean to be fully accountable for past actions?",
        ],
        "activity": "Consequences inventory: each member lists consequences and rates which they are ready to address.",
        "writing_prompt": "Write about one consequence from your use and what you are doing — or could do — about it.",
        "facilitator_tips": "Be sensitive to ongoing legal situations. Do not pressure disclosure. Focus on agency, not shame.",
    },
    {
        "title": "Lapse vs Relapse",
        "category": "Relapse Prevention",
        "description": (
            "Teaches the distinction between a slip and a full relapse and focuses on rapid "
            "course-correction instead of all-or-nothing thinking."
        ),
        "key_points": [
            "Definitions of lapse and relapse",
            "'Abstinence violation effect' and black-and-white thinking",
            "How to respond after a slip without giving up",
        ],
        "discussion_questions": [
            "What does 'one drink = total failure' thinking do to a person?",
            "What would you tell a friend who slipped?",
            "What is your plan if you have a lapse?",
        ],
        "activity": "Scenario cards: read a lapse scenario and role-play the first phone call or action after it happens.",
        "writing_prompt": "Write a plan for what you will do in the first 24 hours after a lapse.",
        "facilitator_tips": "Normalize that lapses happen. The goal is to prevent a lapse from becoming a full relapse.",
    },
    {
        "title": "Early Warning Signs of Relapse",
        "category": "Relapse Prevention",
        "description": (
            "Builds awareness of subtle behavioral, emotional, and thinking changes that typically precede relapse."
        ),
        "key_points": [
            "Common warning signs (isolation, secrecy, romanticizing use)",
            "Personal early-warning signatures",
            "Acting early instead of waiting for crisis",
        ],
        "discussion_questions": [
            "What were the first warning signs before a past relapse?",
            "Who in your life notices before you do?",
            "What is your plan when you see the early signs?",
        ],
        "activity": "Each member creates a personal 'warning sign checklist' and shares one with the group.",
        "writing_prompt": "List five personal warning signs that you are drifting toward relapse.",
        "facilitator_tips": "Help members see warning signs as information, not failure. Early action is strength.",
    },
    {
        "title": "High-Risk Situations and Refusal Skills",
        "category": "Relapse Prevention",
        "description": (
            "Identifies risky situations and teaches concrete ways to say 'no' and exit safely."
        ),
        "key_points": [
            "People, places, and events that raise risk",
            "Assertive refusal language and body posture",
            "Planning exits and backup supports",
        ],
        "discussion_questions": [
            "What is your highest-risk situation right now?",
            "What makes it hard to say no?",
            "What is your exit plan for a situation you cannot avoid?",
        ],
        "activity": "Refusal skills role-play: practice saying no to an offer in three different ways (firm, empathic, redirect).",
        "writing_prompt": "Describe a high-risk situation you are facing and your specific plan to navigate it.",
        "facilitator_tips": "Keep role-plays light but real. Practice builds confidence. Validate that refusal is hard.",
    },
    {
        "title": "Coping with Cravings: Skills Practice",
        "category": "Coping Skills",
        "description": (
            "Provides tools like urge surfing and delay-distract-decide, with in-group practice."
        ),
        "key_points": [
            "Normalizing and rating cravings (0-10 scale)",
            "Urge surfing and grounding skills",
            "Building a personal craving-coping toolbox",
        ],
        "discussion_questions": [
            "What coping skill has worked for you, even once?",
            "What gets in the way of using coping skills in the moment?",
            "How do you know when a craving is starting to peak?",
        ],
        "activity": "Practice urge surfing: members rate a current craving, breathe through it for 5 minutes, and re-rate.",
        "writing_prompt": "Describe your personal craving-coping plan step by step.",
        "facilitator_tips": "Do brief in-group skill practice. Learning by doing beats learning by talking.",
    },
    {
        "title": "Building a Relapse Prevention Plan",
        "category": "Relapse Prevention",
        "description": (
            "Guides members to create individualized, written relapse prevention and crisis plans."
        ),
        "key_points": [
            "Personal triggers and warning signs list",
            "People to call and places to go when at risk",
            "Steps for getting back on track after a slip",
        ],
        "discussion_questions": [
            "What does your relapse prevention plan need that it does not have yet?",
            "Who is on your support list and have you told them?",
            "What is the single most important thing in your plan?",
        ],
        "activity": "Members complete a structured relapse prevention plan template during group.",
        "writing_prompt": "Write out your complete relapse prevention plan in your own words.",
        "facilitator_tips": "A written plan is more likely to be used. Push for specifics — names, numbers, places.",
    },
    {
        "title": "Weekends, Holidays, and Special Events",
        "category": "Relapse Prevention",
        "description": (
            "Focuses on times when routines change and exposure to substances or stress is higher."
        ),
        "key_points": [
            "Identifying upcoming high-risk dates and events",
            "Sober plans, exit strategies, and accountability partners",
            "Coping with FOMO, loneliness, and family stress",
        ],
        "discussion_questions": [
            "What upcoming event or date feels most risky?",
            "How did you used to spend weekends/holidays while using?",
            "What does a sober holiday actually look like for you?",
        ],
        "activity": "Plan a sober weekend: each member maps out a realistic, enjoyable sober weekend plan.",
        "writing_prompt": "Describe your plan for the next holiday or weekend where you typically feel at risk.",
        "facilitator_tips": "Be practical. Help members build concrete plans, not vague intentions.",
    },
    {
        "title": "Managing Boredom and Restlessness",
        "category": "Relapse Prevention",
        "description": (
            "Addresses boredom as a major relapse trigger and promotes values-based, sober activities."
        ),
        "key_points": [
            "How boredom shows up for each person",
            "Unhelpful vs helpful ways of dealing with boredom",
            "Brainstorming low-cost, sober activities and structure",
        ],
        "discussion_questions": [
            "What did you do with free time before using?",
            "What activities are still possible and enjoyable sober?",
            "How much unstructured time do you have per week?",
        ],
        "activity": "Activity menu: group generates a list of 20 free or low-cost sober activities. Members pick three to try.",
        "writing_prompt": "Describe what an enjoyable, full sober day looks like for you.",
        "facilitator_tips": "Boredom is underrated as a relapse driver. Take it seriously. Practical ideas beat lectures.",
    },
    {
        "title": "Sleep, Fatigue, and Relapse Risk",
        "category": "Practical Life Skills",
        "description": (
            "Explores sleep problems common in recovery and how sleep deprivation increases relapse vulnerability."
        ),
        "key_points": [
            "How sleep and mood/cravings interact",
            "Basic sleep hygiene habits",
            "When to seek medical evaluation for sleep issues",
        ],
        "discussion_questions": [
            "How has your sleep changed since you stopped using?",
            "What gets in the way of a good night's sleep?",
            "Have you talked to a doctor about sleep problems?",
        ],
        "activity": "Sleep log review: members track sleep for one week and identify patterns.",
        "writing_prompt": "Describe your current sleep situation and one thing you could change tonight.",
        "facilitator_tips": "Sleep problems in early recovery are nearly universal. Normalize and provide practical steps.",
    },
    {
        "title": "Substance Use and Suicide/Crisis Safety Planning",
        "category": "Mental Health",
        "description": (
            "Links SUD to suicide risk, normalizes talking about it, and develops safety plans including crisis resources."
        ),
        "key_points": [
            "Risk factors: intoxication, withdrawal, impulsivity",
            "Warning signs in self and others",
            "Creating and sharing a written safety plan",
        ],
        "discussion_questions": [
            "Has substance use ever made dark thoughts worse?",
            "Who do you call when things feel really bad?",
            "What would stop you from reaching out when you are in crisis?",
        ],
        "activity": "Safety plan template: members complete a personal safety plan (warning signs, coping steps, people to call, crisis line).",
        "writing_prompt": "Write out your personal safety plan.",
        "facilitator_tips": (
            "Do a safety check before and after this group. Have crisis numbers ready. "
            "This topic requires a co-facilitator if possible."
        ),
    },
    {
        "title": "Long-Term Recovery Maintenance",
        "category": "Relapse Prevention",
        "description": (
            "Addresses life-long recovery tasks: monitoring complacency, ongoing growth, and protecting gains."
        ),
        "key_points": [
            "'Complacency traps' and overconfidence",
            "Continuing care: therapy, groups, sponsors, supports",
            "Balancing recovery with work, family, and goals",
        ],
        "discussion_questions": [
            "What does long-term recovery mean to you?",
            "What do you need to keep doing after this program ends?",
            "What will you do when recovery starts to feel less urgent?",
        ],
        "activity": "Continuing care plan: members map out their post-discharge support network and schedule.",
        "writing_prompt": "Describe your vision for your life in recovery three years from now.",
        "facilitator_tips": "Celebrate progress without minimizing ongoing vigilance. Complacency is real and normal.",
    },
    {
        "title": "CBT Basics: Thoughts, Feelings, Behaviors",
        "category": "Coping Skills",
        "description": (
            "Introduces the CBT model and shows how thoughts, emotions, and behaviors interact in addiction and mental health."
        ),
        "key_points": [
            "The CBT triangle and personal examples",
            "How automatic thoughts drive urges and mood",
            "Using CBT to create alternative responses",
        ],
        "discussion_questions": [
            "What automatic thought most often leads you toward using?",
            "What feeling does that thought usually bring?",
            "What behavior tends to follow?",
        ],
        "activity": "CBT triangle worksheet: members fill in a recent situation with the thought, feeling, and behavior.",
        "writing_prompt": "Write about a recent situation using the CBT triangle (thought, feeling, behavior).",
        "facilitator_tips": "Keep it concrete. Abstract theory loses groups. Use group members' real examples (with permission).",
    },
    {
        "title": "Challenging Unhelpful Thoughts",
        "category": "Coping Skills",
        "description": (
            "Teaches common thinking errors and basic cognitive restructuring steps."
        ),
        "key_points": [
            "Common cognitive distortions in SUD and depression/anxiety",
            "Evidence-for/evidence-against exercise",
            "Creating balanced replacement thoughts",
        ],
        "discussion_questions": [
            "Which thinking error do you fall into most often?",
            "What evidence do you have that your most common negative thought is true?",
            "What evidence says otherwise?",
        ],
        "activity": "Thought record: members identify a distorted thought and work through the evidence for and against it.",
        "writing_prompt": "Identify one unhelpful thought and write a more balanced alternative.",
        "facilitator_tips": "Challenging thoughts takes practice. Keep it collaborative, not confrontational.",
    },
    {
        "title": "Emotional Awareness and Naming Feelings",
        "category": "Emotional Skills",
        "description": (
            "Helps clients increase emotional vocabulary and recognize body cues linked to feelings."
        ),
        "key_points": [
            "Differentiating primary vs secondary emotions",
            "Body cues for different feelings",
            "Using emotion words instead of numbing or acting out",
        ],
        "discussion_questions": [
            "How many emotions can you name right now?",
            "Where do you feel emotions in your body?",
            "What emotion is hardest for you to sit with?",
        ],
        "activity": "Feelings wheel: members use a feelings wheel to identify and share a current emotion.",
        "writing_prompt": "Describe your emotional experience today from morning until now.",
        "facilitator_tips": "Many SUD clients have limited emotional vocabulary. Build it gently with a feelings chart.",
    },
    {
        "title": "Distress Tolerance Skills",
        "category": "Coping Skills",
        "description": (
            "Focuses on surviving emotional crises without making them worse, using DBT-informed tools."
        ),
        "key_points": [
            "When to use distress tolerance vs problem solving",
            "Quick in-the-moment skills (temperature, breathing, movement)",
            "Safe distractions and sensory-based self-soothing",
        ],
        "discussion_questions": [
            "What is a situation you cannot change but need to survive?",
            "What has helped you get through really hard moments before?",
            "What sensory experiences calm you down?",
        ],
        "activity": "Practice the TIPP skill (Temperature, Intense exercise, Paced breathing, Progressive relaxation) as a group.",
        "writing_prompt": "Describe a distress tolerance plan for your most difficult emotional state.",
        "facilitator_tips": "Teach and practice skills in group — do not just list them. Embodied learning sticks.",
    },
    {
        "title": "Emotion Regulation Skills for Recovery",
        "category": "Emotional Skills",
        "description": (
            "Builds skills to reduce vulnerability to intense emotion through lifestyle management."
        ),
        "key_points": [
            "Emotion check-ins and tracking",
            "Reducing vulnerability (sleep, food, medications, routine)",
            "Planning daily positive experiences",
        ],
        "discussion_questions": [
            "What makes you most emotionally vulnerable?",
            "How do you currently track your mood?",
            "What one positive experience could you plan this week?",
        ],
        "activity": "PLEASE skill worksheet: members assess their current sleep, eating, activity, and medication adherence.",
        "writing_prompt": "Plan one positive experience for tomorrow and describe what it will feel like.",
        "facilitator_tips": "Connect emotion regulation directly to relapse risk — unstable emotions are triggers.",
    },
    {
        "title": "Anger Management and Conflict De-Escalation",
        "category": "Emotional Skills",
        "description": (
            "Explores anger triggers and skills to respond without aggression or use."
        ),
        "key_points": [
            "Anger warning signs and body cues",
            "Anger 'iceberg' (what's underneath)",
            "Time-outs, 'I' statements, and problem-solving steps",
        ],
        "discussion_questions": [
            "What does anger feel like in your body before it escalates?",
            "What emotion is usually under the anger?",
            "What does taking a time-out actually look like for you?",
        ],
        "activity": "Anger iceberg: members draw an iceberg and fill in anger on top and underlying emotions below the waterline.",
        "writing_prompt": "Describe a recent situation that made you angry — what was underneath?",
        "facilitator_tips": "Validate anger before teaching skills. Anger is often covering hurt, fear, or grief.",
    },
    {
        "title": "Managing Anxiety and Panic in Recovery",
        "category": "Mental Health",
        "description": (
            "Provides psychoeducation and basic CBT strategies for anxiety, emphasizing non-substance coping."
        ),
        "key_points": [
            "What anxiety is and isn't",
            "Avoidance vs gradual exposure",
            "Breathing, grounding, and realistic thinking",
        ],
        "discussion_questions": [
            "How does anxiety show up in your body?",
            "What do you usually do when anxiety hits?",
            "What would you try if your usual strategy was not available?",
        ],
        "activity": "4-7-8 breathing practice: inhale 4 counts, hold 7, exhale 8. Repeat 4 times together.",
        "writing_prompt": "Describe your anxiety triggers and your current coping plan.",
        "facilitator_tips": "Anxiety is extremely common in SUD recovery. Normalize and teach practical skills.",
    },
    {
        "title": "Managing Depression and Low Motivation",
        "category": "Mental Health",
        "description": (
            "Covers behavioral activation and CBT tools to address depression that often co-occurs with SUD."
        ),
        "key_points": [
            "Depression symptoms vs normal sadness",
            "Activity scheduling and 'do first, feel later'",
            "How isolation and rumination increase use risk",
        ],
        "discussion_questions": [
            "What does depression feel like for you?",
            "What activities used to bring you joy?",
            "What is one small action you could take today, even if you don't feel like it?",
        ],
        "activity": "Activity scheduling: members plan three small pleasurable activities for the next week.",
        "writing_prompt": "Write about one thing that has helped you move even slightly when depression is heavy.",
        "facilitator_tips": "Behavioral activation before motivation — action creates energy, not the other way around.",
    },
    {
        "title": "Mindfulness for Cravings and Emotions",
        "category": "Coping Skills",
        "description": (
            "Introduces mindfulness as present-moment, non-judgmental awareness and practices brief exercises."
        ),
        "key_points": [
            "What mindfulness is (and is not)",
            "Short practices: mindful breathing, body scan, five senses",
            "Using mindfulness with cravings and strong emotions",
        ],
        "discussion_questions": [
            "What does it mean to notice without judging?",
            "What gets in the way of staying present for you?",
            "How could mindfulness help with cravings?",
        ],
        "activity": "Guided 5-minute body scan or 5-senses grounding exercise as a group.",
        "writing_prompt": "Write about your experience during today's mindfulness exercise.",
        "facilitator_tips": "Keep practice short and explain it is not about clearing the mind — just noticing.",
    },
    {
        "title": "Problem-Solving and Decision-Making Skills",
        "category": "Coping Skills",
        "description": (
            "Teaches a structured approach to solving practical and interpersonal problems without substances."
        ),
        "key_points": [
            "Defining the problem clearly",
            "Brainstorming options and weighing pros/cons",
            "Choosing and testing a plan, then reviewing outcomes",
        ],
        "discussion_questions": [
            "What is a problem you have been avoiding?",
            "How do you usually make decisions under stress?",
            "What would it look like to approach this problem step by step?",
        ],
        "activity": "Problem-solving worksheet: members work through a current problem using the five-step model.",
        "writing_prompt": "Pick one current problem and write out a step-by-step plan to address it.",
        "facilitator_tips": "Impulsive decision-making is common in SUD. Teach slowing down as a skill.",
    },
    {
        "title": "Healthy Communication and Assertiveness",
        "category": "Relationships",
        "description": (
            "Focuses on clear, respectful communication and saying what you need without aggression or passivity."
        ),
        "key_points": [
            "Passive, aggressive, and assertive styles",
            "Using 'I' statements and active listening",
            "Practicing assertive requests and boundaries",
        ],
        "discussion_questions": [
            "Which communication style do you tend to default to under stress?",
            "What makes it hard to be assertive?",
            "What is one thing you need to communicate this week?",
        ],
        "activity": "Assertiveness role-play: practice making an assertive request in pairs.",
        "writing_prompt": "Write an assertive message you have been avoiding sending.",
        "facilitator_tips": "Assertiveness is a learned skill. Keep role-plays specific and low-stakes to start.",
    },
    {
        "title": "Boundaries and Codependency in Recovery",
        "category": "Relationships",
        "description": (
            "Explains healthy vs unhealthy boundaries and how codependent patterns can fuel relapse."
        ),
        "key_points": [
            "Types of boundaries (physical, emotional, time, money)",
            "Signs of codependency and enabling",
            "Setting and maintaining limits with others",
        ],
        "discussion_questions": [
            "What is one boundary you struggle to hold?",
            "Where did you learn that your needs do not matter?",
            "What does enabling look like in your relationships?",
        ],
        "activity": "Boundary inventory: members rate their boundaries in different life areas (family, work, romantic, friends).",
        "writing_prompt": "Describe one boundary you need to set and what gets in the way.",
        "facilitator_tips": "Codependency is deeply tied to shame. Approach with warmth and zero blame.",
    },
    {
        "title": "Loneliness, Isolation, and Building Connection",
        "category": "Relationships",
        "description": (
            "Addresses loneliness as a risk factor and explores ways to build safe, supportive connections."
        ),
        "key_points": [
            "How isolation shows up in your life",
            "Balancing alone time vs connection",
            "Practical steps to meet supportive people",
        ],
        "discussion_questions": [
            "When do you feel most alone?",
            "What makes reaching out hard?",
            "Who in your life makes you feel safe?",
        ],
        "activity": "Connection map: members draw their current support network and identify gaps.",
        "writing_prompt": "Describe one step you could take this week to reduce isolation.",
        "facilitator_tips": "Loneliness is a core relapse risk. Validate without minimizing. Help members build concrete steps.",
    },
    {
        "title": "Family Roles, Communication, and Recovery",
        "category": "Relationships",
        "description": (
            "Looks at family interaction patterns and ways to shift conversations toward support instead of conflict."
        ),
        "key_points": [
            "Common family roles in addiction",
            "Unhelpful communication cycles (blame, shutdown, escalation)",
            "Scripts for difficult conversations about recovery",
        ],
        "discussion_questions": [
            "What role does your family expect you to play?",
            "What conversation have you been avoiding with family?",
            "What would a healthy family interaction look like?",
        ],
        "activity": "Script writing: members write out a difficult conversation they need to have with a family member.",
        "writing_prompt": "Write what you wish your family understood about your recovery.",
        "facilitator_tips": "Family dynamics are loaded. Keep focus on the member's behavior, not the family's.",
    },
    {
        "title": "Peer Support, 12-Step, and Alternatives",
        "category": "Relapse Prevention",
        "description": (
            "Introduces different recovery fellowships and how to get the most out of meetings or groups."
        ),
        "key_points": [
            "Types of peer-support programs (12-step, SMART, etc.)",
            "What to expect at a meeting",
            "Choosing a group, sponsor/mentor, or peer support",
        ],
        "discussion_questions": [
            "Have you attended any peer support meetings? What was that like?",
            "What would make it easier to attend regularly?",
            "What do you need from a support community?",
        ],
        "activity": "Meeting list review: members identify three meetings or groups they could attend this week.",
        "writing_prompt": "Write about your experience with or openness to peer support.",
        "facilitator_tips": "Present all options non-judgmentally. Not everyone connects with 12-step — validate alternatives.",
    },
    {
        "title": "Romantic Relationships, Intimacy, and Recovery",
        "category": "Relationships",
        "description": (
            "Explores how substance use and mental health affect intimacy and how to approach relationships in early recovery."
        ),
        "key_points": [
            "Common relationship pitfalls early in recovery",
            "Guidelines and boundaries around dating",
            "Building emotional intimacy without substances",
        ],
        "discussion_questions": [
            "How has your use affected intimate relationships?",
            "What does healthy intimacy look like to you?",
            "What boundaries do you need in a relationship right now?",
        ],
        "activity": "Relationship values exercise: members list their top five values in a romantic partner.",
        "writing_prompt": "Write about what you are looking for in relationships now vs before recovery.",
        "facilitator_tips": "This topic can be highly activating. Maintain boundaries in disclosure. Keep it psychoeducational.",
    },
    {
        "title": "Communicating About Triggers with Loved Ones",
        "category": "Relationships",
        "description": (
            "Teaches how to explain personal triggers and safety needs to supportive people in a concrete way."
        ),
        "key_points": [
            "Identifying what others need to know",
            "Scripts for asking for support",
            "Responding when others do not understand",
        ],
        "discussion_questions": [
            "Does your support network know your triggers?",
            "What is hard about asking for help?",
            "How do you respond when someone does not take your triggers seriously?",
        ],
        "activity": "Practice script: members write and practice a conversation explaining a trigger to a trusted person.",
        "writing_prompt": "Write a message to someone in your life explaining one of your triggers and what you need.",
        "facilitator_tips": "Many clients have never named their triggers to anyone. This is powerful and vulnerable work.",
    },
    {
        "title": "Rebuilding Trust and Making Amends",
        "category": "Relationships",
        "description": (
            "Connects relapse prevention with honesty, consistency, and thoughtful amends where appropriate."
        ),
        "key_points": [
            "What trust is and how it's rebuilt",
            "Difference between apologies and amends",
            "When making contact may not be safe or appropriate",
        ],
        "discussion_questions": [
            "Who do you most want to repair trust with?",
            "What is the difference between apologizing and making amends?",
            "What would rebuilding trust require from you over time?",
        ],
        "activity": "Amends letter (not necessarily to be sent): members write an amends letter to one person.",
        "writing_prompt": "Write about what rebuilding one important relationship would look like step by step.",
        "facilitator_tips": "Amends work is powerful but should not be rushed. Emphasize that direct amends are not always appropriate.",
    },
    {
        "title": "Work/School Issues and Recovery",
        "category": "Practical Life Skills",
        "description": (
            "Addresses disclosure, accommodations, stress, and boundaries related to work or school."
        ),
        "key_points": [
            "Pros/cons of telling employers/teachers about recovery",
            "Handling triggers at work/school",
            "Time management and self-care around responsibilities",
        ],
        "discussion_questions": [
            "What is your biggest stressor related to work or school?",
            "Have you told anyone at work or school about your recovery?",
            "What boundaries do you need at work or school?",
        ],
        "activity": "Disclosure pros/cons worksheet: members weigh the costs and benefits of disclosing their recovery.",
        "writing_prompt": "Describe your work/school situation and how recovery affects it.",
        "facilitator_tips": "Be careful about encouraging disclosure — it can have real consequences. Help members decide for themselves.",
    },
    {
        "title": "Social Media, Technology, and Triggers",
        "category": "Relapse Prevention",
        "description": (
            "Explores how online content can trigger cravings, comparison, or mood swings."
        ),
        "key_points": [
            "Identifying triggering or draining online spaces",
            "Boundaries around time, content, and people online",
            "Curating feeds to support recovery and mental health",
        ],
        "discussion_questions": [
            "What online spaces or people drain or trigger you?",
            "How much time do you spend on social media per day?",
            "What would a healthier relationship with technology look like?",
        ],
        "activity": "Social media audit: members review accounts they follow and identify three to unfollow or mute.",
        "writing_prompt": "Write your personal technology boundaries for recovery.",
        "facilitator_tips": "This is highly relevant for younger members. Take it seriously — social media is a real trigger.",
    },
    {
        "title": "Trauma and PTSD in the Context of Addiction",
        "category": "Mental Health",
        "description": (
            "Provides psychoeducation on trauma, PTSD, and why many people use substances to cope."
        ),
        "key_points": [
            "What trauma and PTSD are (and are not)",
            "How trauma symptoms can drive substance use",
            "Grounding skills and when to seek trauma-focused therapy",
        ],
        "discussion_questions": [
            "How has trauma played a role in your use?",
            "What helps you feel safe when trauma symptoms hit?",
            "What does trauma-informed care mean to you?",
        ],
        "activity": "Grounding exercise: 5-4-3-2-1 sensory grounding practiced together.",
        "writing_prompt": "Write about how trauma has shaped your relationship with substances.",
        "facilitator_tips": (
            "Do NOT facilitate trauma processing in a psychoeducation group. "
            "Provide psychoeducation and grounding only. Refer for individual trauma therapy."
        ),
    },
    {
        "title": "Grief, Loss, and Recovery",
        "category": "Emotional Skills",
        "description": (
            "Addresses grief related to death, relationships, health, and 'lost years' from addiction."
        ),
        "key_points": [
            "Types of loss (people, opportunities, self-image)",
            "Myths about 'getting over' grief",
            "Healthy ways to express and process grief",
        ],
        "discussion_questions": [
            "What have you lost because of your addiction?",
            "What do you grieve that no one around you acknowledges?",
            "How do you carry loss without using?",
        ],
        "activity": "Loss inventory: members list losses and identify which feel most unresolved.",
        "writing_prompt": "Write a letter to something or someone you have lost to addiction.",
        "facilitator_tips": "Grief in SUD recovery is layered and often unacknowledged. Hold space for it with care.",
    },
    {
        "title": "Identity, Self-Esteem, and Rebuilding Self-Worth",
        "category": "Identity & Recovery",
        "description": (
            "Helps clients separate their identity from their illness and build a more compassionate self-view."
        ),
        "key_points": [
            "Messages you absorbed about yourself from addiction and others",
            "Challenging shame-based self-statements",
            "Building a strengths-based recovery identity",
        ],
        "discussion_questions": [
            "Who were you before addiction took over?",
            "What strengths have you shown in recovery so far?",
            "What do you want your identity to be built on going forward?",
        ],
        "activity": "Strengths inventory: members list 10 personal strengths and share three with the group.",
        "writing_prompt": "Write about who you are becoming in recovery.",
        "facilitator_tips": "Go slow. Identity work is deep. Celebrate every strength members can name.",
    },
    {
        "title": "Values Clarification and Life Direction",
        "category": "Identity & Recovery",
        "description": (
            "Uses values work to help clients define what truly matters and align daily actions with those values."
        ),
        "key_points": [
            "Distinguishing values from goals and feelings",
            "Identifying top personal values (family, honesty, health, etc.)",
            "Small daily actions in line with chosen values",
        ],
        "discussion_questions": [
            "What matters most to you now that you are in recovery?",
            "Is how you spend your time aligned with what you value?",
            "What one small action could honor a core value this week?",
        ],
        "activity": "Values sort: members rank a list of 20 values and share their top three with the group.",
        "writing_prompt": "Write about your top three values and how your recovery is or is not reflecting them.",
        "facilitator_tips": "Values work helps members build intrinsic motivation. Keep it personal and non-judgmental.",
    },
    {
        "title": "Spirituality, Meaning, and Purpose in Recovery",
        "category": "Identity & Recovery",
        "description": (
            "Explores spirituality broadly as a source of meaning and resilience, not tied to any religion."
        ),
        "key_points": [
            "Definitions of spirituality and meaning",
            "Ways people experience connection (nature, service, community)",
            "Personal practices that support a sense of purpose",
        ],
        "discussion_questions": [
            "What gives your life meaning right now?",
            "Do you have a spiritual practice or something like one?",
            "What would it mean to live with more purpose?",
        ],
        "activity": "Meaning map: members draw or list what gives them meaning, purpose, and connection.",
        "writing_prompt": "Write about where you find meaning in your life today.",
        "facilitator_tips": "Be explicitly inclusive of all spiritual and non-spiritual perspectives. Do not push any framework.",
    },
    {
        "title": "Telling Your Recovery Story Safely",
        "category": "Identity & Recovery",
        "description": (
            "Supports participants in sharing parts of their story in a way that is empowering and boundaried."
        ),
        "key_points": [
            "What you want to share vs keep private",
            "Focusing on strengths and growth, not just damage",
            "Practicing short 'recovery story' introductions",
        ],
        "discussion_questions": [
            "What parts of your story do you want to share? What do you keep private?",
            "What is the most important thing about your story?",
            "How does telling your story help or complicate things?",
        ],
        "activity": "Each member writes a 2-3 sentence recovery story intro and shares with the group.",
        "writing_prompt": "Write a brief recovery story that focuses on your strength and growth.",
        "facilitator_tips": "Honor confidentiality explicitly before this group. Help members find their story of resilience.",
    },
    {
        "title": "Physical Health, Nutrition, and Exercise in Recovery",
        "category": "Practical Life Skills",
        "description": (
            "Explains how movement and nutrition support mood stability, energy, and relapse prevention."
        ),
        "key_points": [
            "Effects of substances and withdrawal on the body",
            "Simple, realistic steps toward better nutrition",
            "Low-barrier ways to move your body safely",
        ],
        "discussion_questions": [
            "How is your physical health different since stopping use?",
            "What gets in the way of eating well or exercising?",
            "What is one physical health step you could take this week?",
        ],
        "activity": "Wellness plan: members set one nutrition and one movement goal for the week.",
        "writing_prompt": "Write about your current physical health and what recovery has changed.",
        "facilitator_tips": "Keep it accessible. Many members have real barriers to nutrition and exercise — validate this.",
    },
    {
        "title": "Daily Structure, Time Management, and Routines",
        "category": "Practical Life Skills",
        "description": (
            "Shows how predictable routines reduce risk and support mental health and recovery progress."
        ),
        "key_points": [
            "Benefits of a daily schedule in early recovery",
            "Building anchors: wake time, meals, meetings, movement",
            "Planning for unstructured time (evenings, weekends)",
        ],
        "discussion_questions": [
            "What does a typical day look like for you right now?",
            "When do you feel most at risk in your daily schedule?",
            "What one routine could make the biggest difference?",
        ],
        "activity": "Daily schedule template: members fill in an ideal sober daily schedule.",
        "writing_prompt": "Write your ideal daily routine and what it would take to make it real.",
        "facilitator_tips": "Structure is recovery-protective. Help members build one anchor habit at a time.",
    },
    {
        "title": "Self-Care and Self-Compassion Practices",
        "category": "Practical Life Skills",
        "description": (
            "Normalizes self-care as essential, not selfish, and introduces practical, low-cost options."
        ),
        "key_points": [
            "Myths about self-care and 'deserving' rest",
            "Quick daily practices (hygiene, rest, hobbies, connection)",
            "Using self-talk that is realistic and kind",
        ],
        "discussion_questions": [
            "What gets in the way of taking care of yourself?",
            "What is one thing you do that is just for you?",
            "What would you say to a friend who said they did not deserve rest?",
        ],
        "activity": "Self-care menu: members create a personalized list of self-care practices they will actually do.",
        "writing_prompt": "Write a self-care plan for the next seven days.",
        "facilitator_tips": "Many clients in SUD recovery have profound self-neglect. Build in permission and practicality.",
    },
    {
        "title": "Aftercare Planning and Community Resources",
        "category": "Practical Life Skills",
        "description": (
            "Helps participants build a concrete plan for supports, services, and routines after discharge."
        ),
        "key_points": [
            "Mapping out appointments, groups, and supports post-program",
            "Housing, transportation, employment/education resources",
            "What to do in the first 24-72 hours if cravings spike or stress hits",
        ],
        "discussion_questions": [
            "What is your biggest worry about leaving this program?",
            "What supports do you already have lined up?",
            "What is your plan for the first 72 hours after discharge?",
        ],
        "activity": "Aftercare plan worksheet: members complete a structured discharge plan with appointments and contacts.",
        "writing_prompt": "Write your aftercare plan in full detail.",
        "facilitator_tips": "Make this practical and specific. Vague plans are not plans. Get names, dates, and numbers.",
    },
]


STARTER_PLAYLISTS = [
    {
        "title": "Recovery Education — Starter Playlist",
        "youtube_playlist_url": "https://youtube.com/playlist?list=PLtAXzvuI-cJdbNMBGE9bmsdHFpjNzwZAP&si=6T6jlSW-PzILdtUp",
        "description": "A curated starter playlist for SUD/MH group education.",
        "category": "Addiction Education",
        "tags": ["recovery", "education", "SUD", "mental health"],
    },
]


def seed_topics(db) -> int:
    """Insert seeded topics if they do not already exist. Returns count inserted."""
    if db.is_seeded():
        logger.info("[GROUPS] Seed topics already present — skipping.")
        return 0

    inserted = 0
    for topic in SEEDED_TOPICS:
        try:
            db.create_topic({
                **topic,
                "source": "seeded",
                "created_by": "system",
            })
            inserted += 1
        except Exception as exc:
            logger.warning(f"[GROUPS] Failed to seed topic '{topic['title']}': {exc}")

    logger.info(f"[GROUPS] Seeded {inserted} group topics.")
    return inserted


def seed_playlists(db) -> int:
    """Seed starter playlists if none exist yet. Returns count inserted."""
    existing = db.list_playlists()
    if existing:
        return 0

    inserted = 0
    for pl in STARTER_PLAYLISTS:
        try:
            db.create_playlist({
                **pl,
                "added_by": "system",
            })
            inserted += 1
        except Exception as exc:
            logger.warning(f"[GROUPS] Failed to seed playlist '{pl['title']}': {exc}")

    if inserted:
        logger.info(f"[GROUPS] Seeded {inserted} starter playlists.")
    return inserted
