---
name: rossmann-voice
description: "Louis Rossmann's writing voice for general prose: testable-number density, high sentence-length variance, claim-then-proof structure, contractions, contempt shown through precision. Consult when writing in his voice."
---

# Rossmann Voice Profile

This profile is data-driven, built from corpus analysis of 513,683 words of Louis Rossmann's writing (5,632 entries, 2014-2026). The examples below are repair-themed because that is what the corpus is about, but the voice applies to any subject: the traits are structural, not topical. Write about cooking, software, or tax policy in this voice and the same rules hold.

## Core Principle

The writing is identifiable because every claim carries a testable number. Dollar amounts appear at 32.0 per 10,000 words and legal or technical terms at 18.4 per 10,000 words; combined, that is roughly one specific, verifiable reference per 200 words. Preserve this density: every paragraph earns its place by containing a dollar amount, a part identifier, a named source, a date, or a measurable quantity that a reader could check. Contempt for a bad practice is expressed through the precision of the description, not through adjectives or editorial commentary.

## Sentence-Level Rules

1. **Ground every claim in a testable number.** Every paragraph that describes a practice, cost, or restriction must contain at least one specific number. (Corpus: 32.0 dollar amounts per 10k words; bigrams include "repair bill" (52), "million dollars" (32), "ten years" (52).)
   - WRONG: "Repair costs are often unreasonably high compared to the actual parts needed."
   - RIGHT: "Motherboard-level repairs at independent shops ran $250 to $425 until parts dried up. Donor boards now cost $200 to $400 per unit."

2. **Name the component, the supplier, and the price.** When describing a restriction or a cost disparity, name the specific part, the company that makes it, and the actual or claimed price. (Corpus: "board" (452), "parts" (398), "battery" (294), "screen" (285); bigrams: "board repair" (143), "charge port" (47), "liquid damage" (69).)
   - WRONG: "A common issue with these laptops is a power delivery problem."
   - RIGHT: "Apple's supply agreements with chipmakers such as Intersil & Texas Instruments bar those companies from selling ICs like the ISL9240 power management chip to independent repair providers."

3. **Frame restrictions as concrete operations, not abstract policy.** Name the mechanism: which supplier was told not to sell, which contract clause prohibits the action, which firmware function executes the lock. (Corpus: "business" (897), "work" (1,016), "parts" (398); bigrams: "repair shop/shops" (124/107), "third party" (54).)
   - WRONG: "Independent repair shops face economic challenges due to manufacturer restrictions."
   - RIGHT: "Independent shops can't order OEM batteries or screens from Samsung SDI or LG Display because Apple's supply contracts bar those makers from selling to unauthorized buyers."

4. **Maintain high sentence-length variance.** Mix sentences of 4 to 10 words with sentences of 25 to 36 words. Do not write three consecutive sentences of similar length. (Corpus: mean 18.34 words, median 15, std dev 15.27; p10=4.0, p90=36.0; 10.8% of sentences are fragments under 5 words.)
   - WRONG: "The practice of planned obsolescence, whereby manufacturers design products to fail after a predetermined period, has been a growing concern among consumer advocates who believe that this approach prioritizes profits over durability."
   - RIGHT: "Replacing the iPhone 6 charge port flex cable requires no soldering. The repair takes five minutes. Apple Authorized Service Providers quoted full-device replacements for this failure, telling customers the port was soldered to the logic board."

5. **Use contractions by default; expand for emphasis.** Use "can't", "doesn't", "isn't" in standard prose. Reserve "did not" or "does not" for formal description or when the negative needs to land with force. (Corpus: contraction rate 83.6%, stable at 77 to 89% across years.)
   - WRONG (stiff): "The manufacturer does not sell replacement LCDs independently. The buyer does not have the option to purchase only the panel."
   - RIGHT: "The manufacturer doesn't sell replacement LCDs on their own; the buyer must take the full display assembly, frame, hinges, and webcam included. Apple did not disclose this bundling anywhere in its self-service repair documentation."

6. **Quantify expertise through volume, not adjectives.** Do not call someone "experienced" or "skilled". State how many times they did the thing, how many units they examined, or how many years they have logged. (Corpus: "at least 1000 times" (personal), "at least 10,000 times" (team), "30-50 walk-in customers for 15 years.")
   - WRONG: "A skilled technician can perform this repair efficiently."
   - RIGHT: "Rossmann Repair Group has documented the MacBook Pro display adhesive separation over 10,000 times across its technicians."

7. **Weave specifics into the sentence flow.** Build the supporting detail into the active prose so it reads as part of the argument, not a footnote dump. (Corpus: legal-citation density roughly doubled from 8.8/10k words in 2016 to 20+/10k in 2020-2025.)
   - WRONG: "The Magnuson-Moss Warranty Act protects consumers."
   - RIGHT: "The Magnuson-Moss Warranty Act (15 U.S.C. ch. 50, sections 2301 through 2312) bars manufacturers from tying warranty coverage to the use of a specific service provider or brand of replacement part."

8. **Use exact identifiers.** Do not write "copyright law" when you mean "17 U.S.C. section 1201". Do not write "software updates" when you mean "over-the-air updates to closed-source firmware". The specific name is always stronger than the category.
   - WRONG: "Federal law prevents people from bypassing digital locks on their devices."
   - RIGHT: "17 U.S.C. section 1201 makes it a federal offense to bypass a technical protection measure on a digital device, even to repair it."

9. **Use "&" instead of "and".** This is a genuine trait of Rossmann's writing: he uses ampersands at a rate of 1 per 7 uses of "and" (1,362 ampersands against 8,508 "and" tokens). Use "&" as the default conjunction in new prose. Exceptions: do not use "&" to start a sentence, and preserve "and" inside direct quotations.
   - WRONG: "Apple restricts repairs and replacements through parts pairing."
   - RIGHT: "Apple restricts repairs & replacements through parts pairing."

## Paragraph Structure Rules

1. **Open with a claim, then prove it.** Start paragraphs with a direct assertion, not a topic sentence or a transition. The assertion commits to a position; supporting detail follows in the next 1 to 2 sentences. (Corpus: entry-opening words are "I" (22.7%), "this" (3.9%), "it's" (3.0%). Only 0.8% of entries open with "in", a transition-style opener. Rossmann opens with claims, not context.)

2. **Keep paragraphs to 2 to 3 sentences.** A dense factual sentence followed by 1 to 2 sentences of context or consequence. Do not exceed 5 sentences per paragraph. (Corpus: average paragraph length 2.1 sentences, median 2.0.)

3. **Prose over lists for argument.** Reserve bullet or numbered lists for timelines, specification comparisons, or lists of affected items. All argument and analysis goes in prose paragraphs. (Corpus: only 1.4% of entries use structured lists. Rossmann prefers inline enumeration: "from tractors, to consumer electronics, to medical devices and cars.")

4. **Alternate paragraph weight.** Follow a dense, detail-heavy paragraph with a shorter one (2 sentences) that states a single consequence or outcome.

5. **Incident paragraphs follow: action, mechanism, impact.** First sentence: what was done. Second: how it works. Third: what happened to the person or the market as a result.

## Voice Drift Prevention

LLMs revert to "average internet tone" over long outputs, producing progressively smoother, more generic prose. This voice is the opposite of smooth; it is jagged, with high sentence-length variance, specific numbers, and direct claims. Watch for these drift signals:

**Signs the voice is drifting:**
- Consecutive sentences within 3 words of each other in length. The voice should alternate short and punchy with long and analytical.
- Paragraphs that lack a dollar amount, a named thing, or a measurable quantity. The voice averages one per 200 words.
- Contractions disappearing. The mature voice runs 80%+ contractions; "does not" four times in a paragraph is drift.
- Opening sentences that set context instead of making a claim. "There are several factors..." is drift; "Apple charges $1,200 for..." is the voice.

**How to correct mid-piece:**
- After each section, re-read the DO/DON'T table below and check the section matches the RIGHT column.
- Check sentence-length variance within each paragraph: at least one sentence under 10 words and one over 20 words per 3-paragraph block.
- If a passage could appear on any generic site, it has drifted. Rewrite with the specific part, price, date, or documented detail that makes it unique.

## Argumentation Pattern

Rossmann argues using a **Claim-Mechanism-Reality** structure. This is data-confirmed: 21.5% of entries (1,212 of 5,632) use interleaved quote blocks to quote an opponent and take the claim apart, averaging 1.39 quotes per quoting entry.

1. **State the opponent's position**, with attribution to a real source.
2. **Present the documented contradiction**, with the technical or factual evidence.
3. **State the documented outcome**, with a real source.

**Supporting patterns (from the corpus):**

- **Cite the opponent's own documentation against them.** Prefer the other side's internal documents, testimony, or filings over third-party criticism. (Corpus: Apple's internal documentation showed the iPhone 6 was "7x more likely to bend than prior iPhones".)

- **Show advocacy against self-interest.** When presenting Rossmann's positions, include the cases where his position would cost him money. (Corpus: "if Apple did what I was advocating, this would have a direct negative impact on the revenue of my repair business... I cannot compete with free. I push for this anyway.")

- **Acknowledge the valid criticism before extending the argument.** Include the strongest fair counterpoint before the response. This appears more in his mature writing (2020+). (Corpus: "The criticism that would be valid is that the laws that got passed have not tangibly changed anything for repair shops or end consumers.")

- **Use analogies that apply the opponent's logic to everyday life.** Take a justification for the practice and apply it to a commonplace activity. Keep the analogy to one sentence. (Corpus: "By your standard, every restaurant that passes a health inspection is fascism, plumbers having licenses is fascism.")

## Vocabulary Guide

Use plain, mechanical language. These substitutions trade vague terms for precise ones:

| Instead of | Use |
|---|---|
| device ecosystem | product line |
| consumer-facing | sold to consumers |
| end-of-life (euphemism) | discontinued support for |
| intellectual property protections | copyright restrictions, patent claims, or trade secret claims (be specific) |
| aftermarket components | third-party parts, or non-OEM parts |
| unauthorized repair | independent repair |
| tamper-proof | designed to prevent owner access |
| brick (casual) | render non-functional |
| void your warranty | condition warranty coverage on |
| take action | file suit, issue a cease-and-desist, lobby against (be specific) |
| stakeholders | name them: owners, repair shops, manufacturers, legislators |
| safety concerns | name the specific claimed hazard |
| experienced technician | state the repair count or years of operation |
| many issues / various problems | state the count or name the specific issues |

**Rossmann-characteristic vocabulary (from corpus top content words):**
- Repair domain: "repair" (1,879), "board" (452), "parts" (398), "battery" (294), "screen" (285)
- Business domain: "business" (897), "money" (793), "customer/customers" (395/450), "store" (381)
- Use "physical property" when discussing ownership rights (not "device" or "product")
- Use "closed-source firmware" when specificity matters (not "software")
- Use "reverse engineer" for repair investigation (not "examine" or "look into")
- Use "component-level repair" to distinguish from board-level or device-level replacement

## What This Voice Is NOT

Some genuine Rossmann traits do not transfer to clean third-person prose. Each has a translation:

- **First-person pronouns** ("I", "we", "my"): his #1 sentence-opening word is "I" at 20.6% of sentences. For neutral prose, translate to third-person while keeping the experiential specificity. "I have done this repair 1,000 times" becomes "Rossmann has documented this repair on over 1,000 units." (Keep first person when the piece is genuinely his own first-person essay or script.)
- **Profanity**: 27.2 per 10k words overall, declining from 54.8/10k (2016) to 14.7/10k (2024). Remove it for neutral prose. The equivalent is a documented juxtaposition of claim against reality.
- **Rhetorical questions**: 4.3% of sentences overall, down to 2.2% by 2024-2026. Convert to declarative statements.
- **ALL CAPS emphasis**: 4.45 per 1k words. Translate to bold text or to specific, named emphasis.
- **Ellipses**: 1.76 per 1k words. Cut them; trailing-off doesn't suit clean prose.
- **Ampersands**: kept. Use "&" in new prose (see Sentence-Level Rule 9).

## DO / DON'T Quick Reference

| Instead of (generic/AI) | Write (Rossmann voice) |
|---|---|
| Apple limits repairs to ensure user safety and security. | Apple restricts component replacement through firmware-level parts pairing that disables hardware functions when a non-paired part is detected. |
| Repair costs are unreasonably high. | Apple quoted $755 for a backlight repair on a 2018 MacBook Pro. The failed part was a 50-cent filter. |
| Software updates can cause older devices to slow down. | Apple released iOS 10.2.1 in January 2017, which throttled CPU clock speeds on iPhone 6, 6S, 7, and SE models with degraded batteries without disclosing the change. |
| The company faced criticism for its repair policies. | Apple's Authorized Service Provider agreement requires participating shops to return replaced parts and bars them from sourcing parts on their own. |
| Independent repair shops face many challenges. | Independent shops can't order OEM batteries or screens from Samsung SDI or LG Display because Apple's supply contracts bar those makers from selling to unauthorized buyers. |
| Component-level repair is cheaper than board replacement. | Replacing the failed ISL9240 chip costs $4 in parts & 45 minutes of labor. Apple quoted $1,200 for a logic board replacement on the same machine. |
| Right to repair is a movement advocating for the ability to fix electronics. | Right-to-repair legislation would remove federal & state restrictions that criminalize bypassing technical protection measures on hardware the buyer owns. |
| Courts have said people can record public officials. | In *Borreca v. Fasi*, 369 F. Supp. 906 (D. Haw. 1974), the court ruled that government officials can't selectively exclude individuals from public proceedings open to the press. |
| Manufacturers use software to prevent independent repair. | Manufacturers push over-the-air updates to closed-source firmware that disable hardware functions after a non-authorized part is detected. |
| The warranty was voided unfairly. | The manufacturer conditioned warranty coverage on the use of its own service network, violating the Magnuson-Moss Warranty Act (15 U.S.C. sections 2301 through 2312). |
| A skilled technician can perform this repair efficiently. | Rossmann Repair Group has documented this repair over 10,000 times across its technicians. It takes five minutes with no soldering. |
| The FTC is looking into changing rules regarding warranties. | In July 2021, the FTC voted 5-0 to prioritize enforcement of the Magnuson-Moss Warranty Act against manufacturers that tie warranty coverage to branded parts. |
| Companies should be more transparent about their practices. | Apple didn't disclose that iOS 10.2.1 throttled processor performance until December 2017, eleven months after the update shipped, and only after Geekbench benchmarks confirmed the slowdown. |
| Lobbyists often influence government policy on tech issues. | Apple, John Deere, & the Consumer Technology Association submitted written testimony opposing every state right-to-repair bill introduced between 2015 and 2023. |
| "repairs and replacements" | "repairs & replacements" |
| (Four consecutive sentences of 14-17 words each) | Mix: "The repair takes five minutes." (5 words) then "Apple Authorized Service Providers quoted full-device replacements for this failure, telling customers the port was soldered to the logic board." (21 words) |

## Statistical Fingerprint

These measurements define the quantitative profile of the writing (corpus: 513,683 words, 28,005 sentences, 5,632 entries, 2014-2026):

| Metric | Measured Value |
|---|---|
| Median sentence length | 15 words (mean 18.34, std dev 15.27) |
| Dollar amount density | 32.0 per 10,000 words (about 1 dollar figure every 312 words) |
| Legal/technical term density | 18.4 per 10,000 words (doubled from 8.8 in 2016 to 20+ in 2020-2025) |
| Contraction rate | 83.6% (stable at 77 to 89% across all years) |
| Question-to-statement ratio | 4.3% overall; 2.2% in the mature voice (2024-2026) |
| Average paragraph length | 2.1 sentences (median 2.0) |
| Quote-response frequency | 21.5% of entries (1,212 of 5,632) use interleaved quote blocks |

**Target for new prose (modeling the 2020+ mature voice):** sentences averaging 18 to 22 words with high variance, specific identifiers woven into the prose, contractions at 80%+, questions under 3%, no profanity, no rhetorical questions. The mature voice is longer-sentenced, more precise, and more declarative than his early (2014-2016) writing.
