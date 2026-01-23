#!/usr/bin/env python3
"""
Expungement Service for Case Management Suite
Comprehensive expungement eligibility engine and workflow management
"""

import logging
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

from .expungement_models import (
    ExpungementCase, EligibilityRuleSet, ExpungementTask, ExpungementDatabase,
    ExpungementEligibilityStatus, ExpungementProcessStage, ExpungementServiceTier
)

logger = logging.getLogger(__name__)

@dataclass
class EligibilityAssessment:
    """Eligibility assessment result"""
    eligible: bool
    eligibility_date: Optional[str]
    wait_period_days: int
    requirements: List[str]
    disqualifying_factors: List[str]
    estimated_timeline: str
    estimated_cost: float
    next_steps: List[str]
    confidence_score: float

@dataclass
class ExpungementQuizResponse:
    """Response to eligibility quiz question"""
    question_id: str
    answer: Any
    follow_up_needed: bool = False

class ExpungementEligibilityEngine:
    """AI-powered eligibility assessment engine with legally-compliant PC 1203.4 checks"""

    def __init__(self):
        self.db = ExpungementDatabase()
        self.jurisdiction_rules = self._load_jurisdiction_rules()

    def check_eligibility_complete(self, conviction_data: Dict) -> Dict[str, Any]:
        """
        LEGALLY COMPLIANT eligibility check for PC 1203.4

        Args:
            conviction_data: Dictionary with all conviction details

        Returns:
            {
                "eligible": bool,
                "pathway": str,  # "PC 1203.4", "PC 1203.42", "PC 1203.4a", "Not Eligible"
                "disqualifying_factors": List[str],
                "warnings": List[str],
                "recommendations": List[str],
                "next_steps": List[str],
                "estimated_cost": float,
                "estimated_timeline_days": int,
                "success_likelihood": str  # "High", "Medium", "Low"
            }
        """

        result = {
            "eligible": False,
            "pathway": "Unknown",
            "disqualifying_factors": [],
            "warnings": [],
            "recommendations": [],
            "next_steps": [],
            "estimated_cost": 120.0,  # Default filing fee
            "estimated_timeline_days": 70,
            "success_likelihood": "Unknown"
        }

        # STEP 1: Check for PERMANENT disqualifiers (sex offenses)
        if self._check_sex_offense_disqualifier(conviction_data, result):
            return result

        # STEP 2: Check probation completion
        if not self._check_probation_completed(conviction_data, result):
            result["pathway"] = "Not Yet Eligible - Probation Incomplete"
            return result

        # STEP 3: Check state prison requirement
        prison_check = self._check_prison_requirement(conviction_data, result)
        if prison_check == "DISQUALIFIED":
            result["pathway"] = "Not Eligible - State Prison"
            return result
        elif prison_check == "PC_1203_42":
            if not self._check_pc_1203_42_eligibility(conviction_data, result):
                return result
            result["pathway"] = "PC 1203.42"
            result["success_likelihood"] = "Medium"

        # STEP 4: Check current legal status
        if not self._check_current_status(conviction_data, result):
            result["pathway"] = "Not Eligible - Active Legal Issues"
            return result

        # STEP 5: Check probation conditions paid/completed
        if not self._check_probation_conditions(conviction_data, result):
            result["pathway"] = "Not Yet Eligible - Conditions Incomplete"
            return result

        # STEP 6: Check for special handling (DUI, violent, etc)
        self._check_special_offenses(conviction_data, result)

        # STEP 7: Calculate specifics
        result["estimated_cost"] = self._calculate_county_filing_fee(conviction_data.get("county"))
        result["estimated_timeline_days"] = self._calculate_timeline(conviction_data)

        if result["pathway"] == "Unknown":
            result["pathway"] = "PC 1203.4"

        if result["success_likelihood"] == "Unknown":
            result["success_likelihood"] = self._assess_success_likelihood(conviction_data, result)

        result["next_steps"] = self._generate_next_steps_detailed(conviction_data, result)
        result["eligible"] = len(result["disqualifying_factors"]) == 0

        return result

    def _check_sex_offense_disqualifier(self, conviction_data: Dict, result: Dict) -> bool:
        """Check for PC 290 sex offenses - PERMANENT disqualifier"""

        DISQUALIFYING_CODES = [
            "PC 286(c)", "PC 288", "PC 288a(c)", "PC 261.5(d)",
            "PC 269", "PC 285", "PC 287"
        ]

        if conviction_data.get("requires_sex_offender_registration"):
            result["disqualifying_factors"].append(
                "PERMANENT DISQUALIFICATION: This conviction requires sex offender "
                "registration under PC 290. Such convictions are NEVER eligible for "
                "expungement under PC 1203.4."
            )
            result["recommendations"].append(
                "Consider Certificate of Rehabilitation as alternative relief."
            )
            return True

        offense_code = conviction_data.get("offense_code", "")
        for code in DISQUALIFYING_CODES:
            if code in offense_code:
                result["disqualifying_factors"].append(
                    f"PERMANENT DISQUALIFICATION: {code} requires sex offender registration."
                )
                return True

        return False

    def _check_probation_completed(self, conviction_data: Dict, result: Dict) -> bool:
        """Check if probation has been completed"""

        if conviction_data.get("probation_granted"):
            if not conviction_data.get("probation_completed"):
                if not conviction_data.get("early_termination_granted"):
                    result["disqualifying_factors"].append(
                        "Probation not completed. Must complete probation OR obtain "
                        "early termination before filing."
                    )

                    prob_end = conviction_data.get("probation_end_date")
                    if prob_end:
                        if isinstance(prob_end, str):
                            prob_end = datetime.fromisoformat(prob_end)
                        days_left = (prob_end - datetime.now()).days
                        if days_left > 0:
                            result["next_steps"].append(
                                f"Wait {days_left} days until probation completes"
                            )

                    result["recommendations"].append(
                        "Consider filing for early termination of probation if you've "
                        "completed at least 50% of your probation with no violations."
                    )
                    return False
        else:
            # No probation granted - PC 1203.4a pathway
            conv_date = conviction_data.get("conviction_date")
            if conv_date:
                if isinstance(conv_date, str):
                    conv_date = datetime.fromisoformat(conv_date)
                years_since = (datetime.now() - conv_date).days / 365.25
                if years_since < 1:
                    result["disqualifying_factors"].append(
                        f"PC 1203.4a requires 1 year wait when no probation granted. "
                        f"{1 - years_since:.1f} years remaining."
                    )
                    return False
                result["pathway"] = "PC 1203.4a"
                result["warnings"].append(
                    "PC 1203.4a: Must show 'honest and upright life' since conviction."
                )

        return True

    def _check_prison_requirement(self, conviction_data: Dict, result: Dict) -> str:
        """
        Check state prison requirement
        Returns: "OK", "PC_1203_42", or "DISQUALIFIED"
        """

        if not conviction_data.get("served_state_prison"):
            return "OK"

        # Served state prison - check for PC 1203.42 exception
        conv_year = conviction_data.get("conviction_year", 0)
        offense_code = conviction_data.get("offense_code", "")

        # Post-2011 realignment cases may qualify under PC 1203.42
        if conv_year >= 2011:
            # Check if offense would be county jail eligible under Prop 47
            PROP_47_CODES = ["PC 459", "PC 470", "PC 476a", "PC 484", "PC 487", "PC 496"]

            if any(code in offense_code for code in PROP_47_CODES):
                result["warnings"].append(
                    "Served state prison but may qualify under PC 1203.42 "
                    "(post-realignment offense that would now be county jail)."
                )
                return "PC_1203_42"

        # Not eligible for PC 1203.42
        result["disqualifying_factors"].append(
            "Served California state prison time. Not eligible under PC 1203.4. "
            "May qualify for Certificate of Rehabilitation instead."
        )
        return "DISQUALIFIED"

    def _check_pc_1203_42_eligibility(self, conviction_data: Dict, result: Dict) -> bool:
        """Check PC 1203.42 specific requirements (2-year wait)"""

        sentence_complete = conviction_data.get("sentence_completion_date")
        if not sentence_complete:
            result["disqualifying_factors"].append(
                "PC 1203.42: Need sentence completion date to verify 2-year wait."
            )
            return False

        if isinstance(sentence_complete, str):
            sentence_complete = datetime.fromisoformat(sentence_complete)

        years_since = (datetime.now() - sentence_complete).days / 365.25

        if years_since < 2:
            result["disqualifying_factors"].append(
                f"PC 1203.42: Must wait 2 years after sentence completion. "
                f"{2 - years_since:.1f} years remaining."
            )
            return False

        result["warnings"].append(
            "IMPORTANT: PC 1203.42 is discretionary. Judge decides if expungement "
            "is 'in the interest of justice.' Not guaranteed."
        )
        result["recommendations"].append(
            "PC 1203.42 cases should hire an attorney. Requires showing 'interest of justice.'"
        )

        return True

    def _check_current_status(self, conviction_data: Dict, result: Dict) -> bool:
        """Check for current legal issues"""

        has_issues = False

        if conviction_data.get("currently_on_probation"):
            result["disqualifying_factors"].append(
                "Currently on probation for another offense. Must complete ALL probation first."
            )
            has_issues = True

        if conviction_data.get("currently_serving_sentence"):
            result["disqualifying_factors"].append(
                "Currently serving a sentence. Must complete ALL sentences first."
            )
            has_issues = True

        if conviction_data.get("pending_charges"):
            result["disqualifying_factors"].append(
                "Currently have pending criminal charges. Must resolve ALL charges first."
            )
            has_issues = True

        return not has_issues

    def _check_probation_conditions(self, conviction_data: Dict, result: Dict) -> bool:
        """Check all probation conditions are satisfied"""

        all_complete = True

        # Only check fines if they exist and aren't marked as paid
        fines_amt = conviction_data.get("fines_total", 0)
        if fines_amt > 0:
            if not conviction_data.get("fines_paid"):
                result["disqualifying_factors"].append(
                    f"Court fines of ${fines_amt:.2f} not paid. All fines must be paid."
                )
                all_complete = False

        # Only check restitution if it exists and isn't marked as paid
        rest_amt = conviction_data.get("restitution_total", 0)
        if rest_amt > 0:
            if not conviction_data.get("restitution_paid"):
                result["disqualifying_factors"].append(
                    f"Restitution of ${rest_amt:.2f} not paid. All restitution must be paid."
                )
                all_complete = False

        # Only check court costs if explicitly mentioned
        if "court_costs_paid" in conviction_data:
            if not conviction_data.get("court_costs_paid"):
                result["disqualifying_factors"].append(
                    "Court costs not paid. All court costs must be paid."
                )
                all_complete = False

        # Only check community service if hours were assigned
        hours = conviction_data.get("community_service_hours", 0)
        if hours > 0:
            if not conviction_data.get("community_service_completed"):
                result["disqualifying_factors"].append(
                    f"Community service ({hours} hours) not completed."
                )
                all_complete = False

        # Only check counseling if it was required
        if conviction_data.get("counseling_required"):
            if not conviction_data.get("counseling_completed"):
                result["disqualifying_factors"].append(
                    "Court-ordered counseling/treatment not completed."
                )
                all_complete = False

        return all_complete

    def _check_special_offenses(self, conviction_data: Dict, result: Dict):
        """Check for offenses requiring special handling"""

        offense_code = conviction_data.get("offense_code", "")

        # DUI - requires "interest of justice" showing
        DUI_CODES = ["VC 23152", "VC 23153"]
        if any(dui in offense_code for dui in DUI_CODES):
            result["warnings"].append(
                "DUI: Eligible but requires showing expungement is 'in the interest "
                "of justice' - HIGHER standard than regular cases."
            )
            result["recommendations"].append(
                "DUI cases: STRONGLY recommend hiring an attorney for 'interest of justice' argument."
            )
            result["success_likelihood"] = "Medium"

        # Violent felonies may face DA objection
        if conviction_data.get("is_violent_felony"):
            result["warnings"].append(
                "Violent felony: May face DA objection. Prepare strong rehabilitation evidence."
            )

        # Wobblers - recommend reduction first
        if conviction_data.get("is_wobbler"):
            if conviction_data.get("conviction_type") == "felony":
                result["recommendations"].append(
                    "WOBBLER: Consider filing for felony reduction to misdemeanor (PC 17(b)) "
                    "BEFORE or WITH expungement petition. Improves chances."
                )

    def _calculate_county_filing_fee(self, county: str) -> float:
        """Get filing fee by county"""
        fees = {
            "Los Angeles": 150,
            "San Diego": 120,
            "Orange": 145,
            "Riverside": 130,
            "San Bernardino": 135,
            "Ventura": 125,
            "San Francisco": 140,
            "Alameda": 135,
            "Sacramento": 125,
            "Contra Costa": 130
        }
        return fees.get(county, 120)  # Default $120

    def _calculate_timeline(self, conviction_data: Dict) -> int:
        """Estimate timeline in days"""
        base_days = 70  # 10 weeks average

        county = conviction_data.get("county", "")
        if county in ["Los Angeles", "San Bernardino"]:
            base_days = 90  # Busier courts
        elif county in ["Orange", "Ventura"]:
            base_days = 50  # Faster courts

        # PC 1203.42 takes longer (hearing required)
        if conviction_data.get("pathway") == "PC 1203.42":
            base_days += 30

        # DUI may require hearing
        if "VC 23152" in conviction_data.get("offense_code", ""):
            base_days += 14

        return base_days

    def _assess_success_likelihood(self, conviction_data: Dict, result: Dict) -> str:
        """Assess likelihood of petition being granted"""

        if conviction_data.get("pathway") == "PC 1203.42":
            return "Medium"  # Discretionary

        if "DUI" in str(conviction_data.get("offense_code", "")):
            return "Medium"  # Higher standard

        if conviction_data.get("is_violent_felony"):
            return "Medium"  # May face objection

        # Clean completion
        if (conviction_data.get("probation_completed") and
            conviction_data.get("fines_paid") and
            conviction_data.get("restitution_paid")):
            return "High"

        return "High"

    def _generate_next_steps_detailed(self, conviction_data: Dict, result: Dict) -> List[str]:
        """Generate actionable next steps"""

        steps = []

        if result["eligible"]:
            steps = [
                "1. Obtain criminal history from California DOJ",
                "2. Get court case file (or DOJ CII if purged)",
                "3. Complete CR-180 form (Petition for Dismissal)",
                "4. Gather rehabilitation evidence (employment, education, community service)",
                f"5. Pay ${result['estimated_cost']:.2f} filing fee or request fee waiver (if eligible)",
                "6. File petition with court clerk",
                "7. Serve copy to District Attorney",
                f"8. Wait for court response ({result['estimated_timeline_days']} days average)"
            ]

            if "hearing" in str(result.get("warnings", "")).lower():
                steps.append("9. Prepare for court hearing (if required)")
        else:
            if "Probation" in str(result["disqualifying_factors"]):
                steps.append("Complete probation OR file for early termination")
            if "fines" in str(result["disqualifying_factors"]).lower():
                steps.append("Pay all outstanding fines")
            if "restitution" in str(result["disqualifying_factors"]).lower():
                steps.append("Pay all restitution to victims")
            if "pending" in str(result["disqualifying_factors"]).lower():
                steps.append("Resolve all pending criminal charges")
            if "community service" in str(result["disqualifying_factors"]).lower():
                steps.append("Complete all court-ordered community service")
            if "counseling" in str(result["disqualifying_factors"]).lower():
                steps.append("Complete all court-ordered counseling/treatment programs")

        return steps
    
    def _load_jurisdiction_rules(self) -> Dict[str, EligibilityRuleSet]:
        """Load jurisdiction-specific rules"""
        # For now, return California rules as default
        ca_rules = EligibilityRuleSet(
            jurisdiction="CA",
            rule_name="California PC 1203.4 Expungement",
            statute_reference="PC 1203.4",
            eligible_offense_types=json.dumps([
                "misdemeanor", "felony_probation", "infraction"
            ]),
            ineligible_offense_types=json.dumps([
                "serious_felony", "violent_felony", "sex_offense_registration"
            ]),
            wait_period_months=0,  # No wait period if probation completed
            probation_completion_required=True,
            fines_payment_required=True,
            no_new_convictions_required=True,
            hearing_required=True,
            filing_fee=150.0,
            fee_waiver_available=True,
            required_documents=json.dumps([
                "petition_form", "case_information", "proof_of_completion",
                "character_references", "employment_verification"
            ]),
            typical_processing_days=90,
            hearing_scheduling_days=30
        )
        
        return {"CA": ca_rules}
    
    def run_eligibility_quiz(self, client_id: str, responses: List[ExpungementQuizResponse]) -> EligibilityAssessment:
        """Run guided eligibility assessment quiz"""
        try:
            # Process quiz responses
            quiz_data = self._process_quiz_responses(responses)
            
            # Determine jurisdiction (default to CA for demo)
            jurisdiction = quiz_data.get('jurisdiction', 'CA')
            rules = self.jurisdiction_rules.get(jurisdiction)
            
            if not rules:
                return self._create_unknown_assessment("Jurisdiction not supported")
            
            # Run eligibility checks
            eligibility_checks = self._run_eligibility_checks(quiz_data, rules)
            
            # Calculate assessment
            assessment = self._calculate_eligibility_assessment(quiz_data, rules, eligibility_checks)
            
            return assessment
            
        except Exception as e:
            logger.error(f"Eligibility quiz error: {e}")
            return self._create_unknown_assessment("Assessment error occurred")
    
    def _process_quiz_responses(self, responses: List[ExpungementQuizResponse]) -> Dict[str, Any]:
        """Process quiz responses into structured data"""
        quiz_data = {}
        
        for response in responses:
            if response.question_id == "conviction_date":
                quiz_data['conviction_date'] = response.answer
            elif response.question_id == "offense_type":
                quiz_data['offense_type'] = response.answer
            elif response.question_id == "offense_code":
                quiz_data['offense_code'] = response.answer
            elif response.question_id == "county":
                quiz_data['county'] = response.answer
            elif response.question_id == "probation_completed":
                quiz_data['probation_completed'] = response.answer
            elif response.question_id == "probation_granted":
                quiz_data['probation_granted'] = response.answer
            elif response.question_id == "early_termination_granted":
                quiz_data['early_termination_granted'] = response.answer
            elif response.question_id == "fines_paid":
                quiz_data['fines_paid'] = response.answer
            elif response.question_id == "fines_total":
                quiz_data['fines_total'] = response.answer
            elif response.question_id == "restitution_paid":
                quiz_data['restitution_paid'] = response.answer
            elif response.question_id == "restitution_total":
                quiz_data['restitution_total'] = response.answer
            elif response.question_id == "court_costs_paid":
                quiz_data['court_costs_paid'] = response.answer
            elif response.question_id == "community_service_completed":
                quiz_data['community_service_completed'] = response.answer
            elif response.question_id == "community_service_hours":
                quiz_data['community_service_hours'] = response.answer
            elif response.question_id == "counseling_required":
                quiz_data['counseling_required'] = response.answer
            elif response.question_id == "counseling_completed":
                quiz_data['counseling_completed'] = response.answer
            elif response.question_id == "requires_sex_offender_registration":
                quiz_data['requires_sex_offender_registration'] = response.answer
            elif response.question_id == "is_violent_felony":
                quiz_data['is_violent_felony'] = response.answer
            elif response.question_id == "is_wobbler":
                quiz_data['is_wobbler'] = response.answer
            elif response.question_id == "served_state_prison":
                quiz_data['served_state_prison'] = response.answer
            elif response.question_id == "sentence_completion_date":
                quiz_data['sentence_completion_date'] = response.answer
            elif response.question_id == "currently_on_probation":
                quiz_data['currently_on_probation'] = response.answer
            elif response.question_id == "currently_serving_sentence":
                quiz_data['currently_serving_sentence'] = response.answer
            elif response.question_id == "pending_charges":
                quiz_data['pending_charges'] = response.answer
            elif response.question_id == "new_convictions":
                quiz_data['new_convictions'] = response.answer
            elif response.question_id == "sentence_type":
                quiz_data['sentence_type'] = response.answer
            elif response.question_id == "jurisdiction":
                quiz_data['jurisdiction'] = response.answer
        
        return quiz_data
    
    def _run_eligibility_checks(self, quiz_data: Dict[str, Any], rules: EligibilityRuleSet) -> Dict[str, bool]:
        """Run individual eligibility checks"""
        checks = {}
        
        # Check offense type eligibility
        offense_type = quiz_data.get('offense_type', '').lower()
        eligible_types = json.loads(rules.eligible_offense_types)
        ineligible_types = json.loads(rules.ineligible_offense_types)
        
        checks['offense_eligible'] = offense_type in eligible_types
        checks['offense_not_disqualified'] = offense_type not in ineligible_types
        
        # Check probation completion
        checks['probation_completed'] = quiz_data.get('probation_completed', False)
        
        # Check fines payment
        checks['fines_paid'] = quiz_data.get('fines_paid', False)
        
        # Check new convictions
        checks['no_new_convictions'] = not quiz_data.get('new_convictions', True)
        
        # Check wait period (if applicable)
        conviction_date = quiz_data.get('conviction_date')
        if conviction_date and rules.wait_period_months > 0:
            try:
                conv_date = datetime.fromisoformat(conviction_date)
                wait_until = conv_date + timedelta(days=rules.wait_period_months * 30)
                checks['wait_period_satisfied'] = datetime.now() >= wait_until
            except:
                checks['wait_period_satisfied'] = False
        else:
            checks['wait_period_satisfied'] = True
        
        return checks
    
    def _calculate_eligibility_assessment(self, quiz_data: Dict[str, Any], rules: EligibilityRuleSet, checks: Dict[str, bool]) -> EligibilityAssessment:
        """Calculate final eligibility assessment"""
        
        # Determine eligibility
        required_checks = [
            'offense_eligible', 'offense_not_disqualified', 
            'probation_completed', 'fines_paid', 'no_new_convictions',
            'wait_period_satisfied'
        ]
        
        eligible = all(checks.get(check, False) for check in required_checks)
        
        # Calculate confidence score
        passed_checks = sum(1 for check in required_checks if checks.get(check, False))
        confidence_score = (passed_checks / len(required_checks)) * 100
        
        # Determine eligibility date
        eligibility_date = None
        wait_period_days = 0
        
        if eligible:
            eligibility_date = datetime.now().isoformat()
        elif not checks.get('wait_period_satisfied', True):
            # Calculate when wait period will be satisfied
            conviction_date = quiz_data.get('conviction_date')
            if conviction_date:
                try:
                    conv_date = datetime.fromisoformat(conviction_date)
                    wait_until = conv_date + timedelta(days=rules.wait_period_months * 30)
                    eligibility_date = wait_until.isoformat()
                    wait_period_days = (wait_until - datetime.now()).days
                except:
                    pass
        
        # Build requirements list
        requirements = []
        if rules.probation_completion_required:
            requirements.append("Complete all probation terms successfully")
        if rules.fines_payment_required:
            requirements.append("Pay all fines, fees, and restitution in full")
        if rules.no_new_convictions_required:
            requirements.append("No new criminal convictions since original case")
        if rules.wait_period_months > 0:
            requirements.append(f"Wait {rules.wait_period_months} months after conviction")
        
        # Build disqualifying factors
        disqualifying_factors = []
        if not checks.get('offense_eligible', True):
            disqualifying_factors.append("Offense type not eligible for expungement")
        if not checks.get('offense_not_disqualified', True):
            disqualifying_factors.append("Offense type specifically excluded from expungement")
        if not checks.get('probation_completed', True):
            disqualifying_factors.append("Probation not completed or violated")
        if not checks.get('fines_paid', True):
            disqualifying_factors.append("Outstanding fines, fees, or restitution")
        if not checks.get('no_new_convictions', True):
            disqualifying_factors.append("New convictions since original case")
        
        # Estimate timeline and cost
        if eligible:
            estimated_timeline = f"{rules.typical_processing_days} days"
            estimated_cost = rules.filing_fee
        else:
            estimated_timeline = "Not eligible at this time"
            estimated_cost = 0.0
        
        # Build next steps
        next_steps = []
        if eligible:
            next_steps = [
                "Gather required documentation",
                "Complete petition forms",
                "File petition with court",
                "Attend court hearing (if required)",
                "Receive court decision"
            ]
        else:
            for factor in disqualifying_factors:
                if "probation" in factor.lower():
                    next_steps.append("Complete probation requirements")
                elif "fines" in factor.lower():
                    next_steps.append("Pay outstanding financial obligations")
                elif "convictions" in factor.lower():
                    next_steps.append("Avoid new criminal convictions")
        
        return EligibilityAssessment(
            eligible=eligible,
            eligibility_date=eligibility_date,
            wait_period_days=wait_period_days,
            requirements=requirements,
            disqualifying_factors=disqualifying_factors,
            estimated_timeline=estimated_timeline,
            estimated_cost=estimated_cost,
            next_steps=next_steps,
            confidence_score=confidence_score
        )
    
    def _create_unknown_assessment(self, reason: str) -> EligibilityAssessment:
        """Create assessment for unknown eligibility"""
        return EligibilityAssessment(
            eligible=False,
            eligibility_date=None,
            wait_period_days=0,
            requirements=["Professional legal consultation required"],
            disqualifying_factors=[reason],
            estimated_timeline="Unknown",
            estimated_cost=0.0,
            next_steps=["Consult with qualified attorney"],
            confidence_score=0.0
        )

class ExpungementWorkflowManager:
    """Manages expungement workflow and task automation"""
    
    def __init__(self):
        self.db = ExpungementDatabase()
        self.eligibility_engine = ExpungementEligibilityEngine()
    
    def create_expungement_case(self, client_id: str, case_data: Dict[str, Any]) -> ExpungementCase:
        """Create new expungement case with automated workflow"""
        try:
            # Create expungement case
            expungement_case = ExpungementCase(
                client_id=client_id,
                **case_data
            )
            
            # Save to database
            self.db.save_expungement_case(expungement_case)
            
            # Generate initial workflow tasks
            self._generate_workflow_tasks(expungement_case)
            
            return expungement_case
            
        except Exception as e:
            logger.error(f"Create expungement case error: {e}")
            raise
    
    def _generate_workflow_tasks(self, case: ExpungementCase):
        """Generate automated workflow tasks based on case stage"""
        try:
            tasks = []
            
            if case.process_stage == ExpungementProcessStage.INTAKE.value:
                tasks.extend(self._generate_intake_tasks(case))
            elif case.process_stage == ExpungementProcessStage.ELIGIBILITY_REVIEW.value:
                tasks.extend(self._generate_eligibility_tasks(case))
            elif case.process_stage == ExpungementProcessStage.DOCUMENT_PREPARATION.value:
                tasks.extend(self._generate_document_tasks(case))
            elif case.process_stage == ExpungementProcessStage.FILING.value:
                tasks.extend(self._generate_filing_tasks(case))
            elif case.process_stage == ExpungementProcessStage.HEARING_SCHEDULED.value:
                tasks.extend(self._generate_hearing_prep_tasks(case))
            
            # Save all tasks
            for task in tasks:
                self.db.save_expungement_task(task)
                
        except Exception as e:
            logger.error(f"Generate workflow tasks error: {e}")
    
    def _generate_intake_tasks(self, case: ExpungementCase) -> List[ExpungementTask]:
        """Generate intake stage tasks"""
        tasks = []
        
        # Initial consultation task
        tasks.append(ExpungementTask(
            expungement_id=case.expungement_id,
            client_id=case.client_id,
            task_type="consultation",
            task_title="Initial Expungement Consultation",
            task_description="Conduct initial consultation to gather case information and assess client needs",
            priority="high",
            due_date=(datetime.now() + timedelta(days=3)).isoformat(),
            assigned_to="case_manager",
            assigned_type="staff",
            estimated_hours=1.5
        ))
        
        # Case information gathering
        tasks.append(ExpungementTask(
            expungement_id=case.expungement_id,
            client_id=case.client_id,
            task_type="information_gathering",
            task_title="Gather Case Information",
            task_description="Collect complete case information, court records, and conviction details",
            priority="high",
            due_date=(datetime.now() + timedelta(days=5)).isoformat(),
            assigned_to="case_manager",
            assigned_type="staff",
            estimated_hours=2.0
        ))
        
        return tasks
    
    def _generate_eligibility_tasks(self, case: ExpungementCase) -> List[ExpungementTask]:
        """Generate eligibility review tasks"""
        tasks = []
        
        # Eligibility assessment
        tasks.append(ExpungementTask(
            expungement_id=case.expungement_id,
            client_id=case.client_id,
            task_type="eligibility_assessment",
            task_title="Complete Eligibility Assessment",
            task_description="Run comprehensive eligibility assessment using guided questionnaire",
            priority="high",
            due_date=(datetime.now() + timedelta(days=2)).isoformat(),
            assigned_to="case_manager",
            assigned_type="staff",
            estimated_hours=1.0
        ))
        
        # Legal research if needed
        tasks.append(ExpungementTask(
            expungement_id=case.expungement_id,
            client_id=case.client_id,
            task_type="legal_research",
            task_title="Legal Research and Verification",
            task_description="Verify eligibility requirements and research any complex legal issues",
            priority="medium",
            due_date=(datetime.now() + timedelta(days=7)).isoformat(),
            assigned_to="attorney",
            assigned_type="attorney",
            estimated_hours=2.0
        ))
        
        return tasks
    
    def _generate_document_tasks(self, case: ExpungementCase) -> List[ExpungementTask]:
        """Generate document preparation tasks"""
        tasks = []
        
        # Document collection
        required_docs = json.loads(case.required_documents) if case.required_documents else []
        
        for doc_type in required_docs:
            tasks.append(ExpungementTask(
                expungement_id=case.expungement_id,
                client_id=case.client_id,
                task_type="document_collection",
                task_title=f"Collect {doc_type.replace('_', ' ').title()}",
                task_description=f"Obtain and prepare {doc_type.replace('_', ' ')} for petition filing",
                priority="high" if doc_type in ["petition_form", "case_information"] else "medium",
                due_date=(datetime.now() + timedelta(days=14)).isoformat(),
                assigned_to="client" if doc_type in ["employment_verification", "character_references"] else "case_manager",
                assigned_type="client" if doc_type in ["employment_verification", "character_references"] else "staff",
                estimated_hours=1.0
            ))
        
        # Petition preparation
        tasks.append(ExpungementTask(
            expungement_id=case.expungement_id,
            client_id=case.client_id,
            task_type="petition_preparation",
            task_title="Prepare Expungement Petition",
            task_description="Complete and review expungement petition forms with all supporting documentation",
            priority="high",
            due_date=(datetime.now() + timedelta(days=21)).isoformat(),
            assigned_to="attorney",
            assigned_type="attorney",
            estimated_hours=3.0
        ))
        
        return tasks
    
    def _generate_filing_tasks(self, case: ExpungementCase) -> List[ExpungementTask]:
        """Generate filing stage tasks"""
        tasks = []
        
        # File petition
        tasks.append(ExpungementTask(
            expungement_id=case.expungement_id,
            client_id=case.client_id,
            task_type="court_filing",
            task_title="File Expungement Petition",
            task_description="File completed petition with appropriate court and pay filing fees",
            priority="high",
            due_date=(datetime.now() + timedelta(days=2)).isoformat(),
            assigned_to="case_manager",
            assigned_type="staff",
            estimated_hours=2.0
        ))
        
        # Track filing status
        tasks.append(ExpungementTask(
            expungement_id=case.expungement_id,
            client_id=case.client_id,
            task_type="status_tracking",
            task_title="Track Filing Status",
            task_description="Monitor petition status and court response",
            priority="medium",
            due_date=(datetime.now() + timedelta(days=14)).isoformat(),
            assigned_to="case_manager",
            assigned_type="staff",
            estimated_hours=0.5
        ))
        
        return tasks
    
    def _generate_hearing_prep_tasks(self, case: ExpungementCase) -> List[ExpungementTask]:
        """Generate hearing preparation tasks"""
        tasks = []
        
        # Client preparation
        tasks.append(ExpungementTask(
            expungement_id=case.expungement_id,
            client_id=case.client_id,
            task_type="hearing_preparation",
            task_title="Prepare Client for Hearing",
            task_description="Meet with client to prepare for court hearing, review process and expectations",
            priority="high",
            due_date=(datetime.now() + timedelta(days=7)).isoformat(),
            assigned_to="attorney",
            assigned_type="attorney",
            estimated_hours=1.5
        ))
        
        # Court appearance
        if case.hearing_date:
            tasks.append(ExpungementTask(
                expungement_id=case.expungement_id,
                client_id=case.client_id,
                task_type="court_appearance",
                task_title="Attend Court Hearing",
                task_description="Attend expungement hearing and represent client",
                priority="urgent",
                due_date=case.hearing_date,
                assigned_to="attorney",
                assigned_type="attorney",
                estimated_hours=3.0
            ))
        
        return tasks
    
    def update_case_stage(self, expungement_id: str, new_stage: str) -> bool:
        """Update case stage and generate new tasks"""
        try:
            # Get current case
            cases = self.db.get_expungement_cases()
            case = next((c for c in cases if c.expungement_id == expungement_id), None)
            
            if not case:
                return False
            
            # Update stage
            case.process_stage = new_stage
            case.last_updated = datetime.now().isoformat()
            
            # Generate new tasks for the stage
            self._generate_workflow_tasks(case)
            
            return True
            
        except Exception as e:
            logger.error(f"Update case stage error: {e}")
            return False
    
    def get_case_progress(self, expungement_id: str) -> Dict[str, Any]:
        """Get comprehensive case progress information"""
        try:
            # Get case
            cases = self.db.get_expungement_cases()
            case = next((c for c in cases if c.expungement_id == expungement_id), None)
            
            if not case:
                return {}
            
            # Get tasks
            tasks = self.db.get_expungement_tasks(expungement_id=expungement_id)
            
            # Calculate progress metrics
            total_tasks = len(tasks)
            completed_tasks = len([t for t in tasks if t.status == 'completed'])
            overdue_tasks = len([t for t in tasks if t.is_overdue])
            
            progress_percentage = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
            
            # Get next actions
            pending_tasks = [t for t in tasks if t.status == 'pending']
            next_actions = sorted(pending_tasks, key=lambda x: (x.priority == 'urgent', x.priority == 'high', x.due_date or ''))[:3]
            
            return {
                'case': case.to_dict(),
                'progress_percentage': progress_percentage,
                'total_tasks': total_tasks,
                'completed_tasks': completed_tasks,
                'overdue_tasks': overdue_tasks,
                'next_actions': [t.to_dict() for t in next_actions],
                'document_completion': case.document_completion_percentage,
                'estimated_completion': self._estimate_completion_date(case, tasks)
            }
            
        except Exception as e:
            logger.error(f"Get case progress error: {e}")
            return {}
    
    def _estimate_completion_date(self, case: ExpungementCase, tasks: List[ExpungementTask]) -> Optional[str]:
        """Estimate case completion date based on remaining tasks"""
        try:
            pending_tasks = [t for t in tasks if t.status != 'completed']
            if not pending_tasks:
                return datetime.now().isoformat()
            
            # Find latest due date
            due_dates = [t.due_date for t in pending_tasks if t.due_date]
            if due_dates:
                latest_due = max(due_dates)
                # Add buffer time based on case complexity
                completion_date = datetime.fromisoformat(latest_due) + timedelta(days=30)
                return completion_date.isoformat()
            
            return None
            
        except Exception as e:
            logger.error(f"Estimate completion date error: {e}")
            return None

class ExpungementDocumentGenerator:
    """Automated document generation for expungement petitions"""
    
    def __init__(self):
        self.templates = self._load_document_templates()
    
    def _load_document_templates(self) -> Dict[str, str]:
        """Load document templates"""
        # For demo purposes, return basic templates
        return {
            "ca_pc_1203_4": """
PETITION FOR DISMISSAL UNDER PENAL CODE SECTION 1203.4

TO THE HONORABLE JUDGE OF THE SUPERIOR COURT:

Petitioner {client_name} respectfully represents:

1. On {conviction_date}, petitioner was convicted of {offense_description} in case number {case_number}.

2. Petitioner was granted probation and has fulfilled all conditions of probation.

3. Petitioner has paid all fines, fees, and restitution ordered by the court.

4. Petitioner is not currently charged with, on probation for, or serving a sentence for any offense.

WHEREFORE, petitioner respectfully requests that this Honorable Court grant this petition and dismiss the charges pursuant to Penal Code Section 1203.4.

Respectfully submitted,

{attorney_name}
Attorney for Petitioner
            """,
            "character_reference_template": """
CHARACTER REFERENCE LETTER

To Whom It May Concern:

I am writing this letter to provide a character reference for {client_name} in support of their petition for expungement.

I have known {client_name} for {relationship_duration} in my capacity as {relationship_type}.

During this time, I have observed {client_name} to be {positive_qualities}.

{specific_examples}

I believe {client_name} has demonstrated genuine rehabilitation and deserves a second chance.

Sincerely,

{reference_name}
{reference_title}
{contact_information}
            """
        }
    
    def generate_petition(self, case: ExpungementCase, template_data: Dict[str, Any]) -> str:
        """Generate expungement petition document"""
        try:
            # Determine template based on jurisdiction and petition type
            template_key = f"{case.jurisdiction.lower()}_{case.petition_type.lower().replace(' ', '_')}"
            template = self.templates.get(template_key, self.templates.get("ca_pc_1203_4"))
            
            # Fill template with case data
            filled_template = template.format(**template_data)
            
            return filled_template
            
        except Exception as e:
            logger.error(f"Generate petition error: {e}")
            return ""
    
    def generate_character_reference_template(self, client_name: str) -> str:
        """Generate character reference template for client"""
        try:
            template = self.templates["character_reference_template"]
            
            # Provide template with placeholders
            template_data = {
                'client_name': client_name,
                'relationship_duration': '[DURATION]',
                'relationship_type': '[RELATIONSHIP TYPE]',
                'positive_qualities': '[POSITIVE QUALITIES]',
                'specific_examples': '[SPECIFIC EXAMPLES]',
                'reference_name': '[REFERENCE NAME]',
                'reference_title': '[REFERENCE TITLE]',
                'contact_information': '[CONTACT INFORMATION]'
            }
            
            return template.format(**template_data)
            
        except Exception as e:
            logger.error(f"Generate character reference template error: {e}")
            return ""
