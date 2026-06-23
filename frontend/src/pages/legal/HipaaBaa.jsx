import React from 'react';
import { ShieldCheck } from 'lucide-react';
import LegalPageLayout, { LegalSection, LegalDisclaimer } from '../../components/LegalPageLayout';

export default function HipaaBaa() {
  return (
    <LegalPageLayout
      icon={ShieldCheck}
      title="HIPAA / BAA"
      subtitle="Business associate considerations for Ember."
    >
      <LegalSection title="Summary">
        <p>
          This page explains, in plain language, how Ember thinks about HIPAA and Business Associate
          Agreements (BAAs). Ember is designed with HIPAA-aware workflows, but no software product is
          "HIPAA certified." Whether and how a BAA applies depends on your organization's role and the
          data it handles.
        </p>
      </LegalSection>

      <LegalSection title="What a BAA is">
        <p>A Business Associate Agreement is a contract under HIPAA between a covered entity (or a business
          associate) and a vendor that creates, receives, maintains, or transmits protected health
          information (PHI) on its behalf. The BAA sets out each party's responsibilities for safeguarding
          that information.</p>
      </LegalSection>

      <LegalSection title="When a BAA may be required">
        <p>A BAA may be required when an organization that is a HIPAA covered entity or business associate
          uses a vendor to handle PHI. Whether your organization needs a BAA depends on your regulatory
          status and how you use the platform — a determination your organization should make with its own
          advisors.</p>
      </LegalSection>

      <LegalSection title="Ember's intended posture">
        <p>Ember is designed to support organizations that operate as covered entities or business
          associates by providing HIPAA-aware workflows such as authentication, role-based access, data
          minimization, and activity logging where currently supported.</p>
      </LegalSection>

      <LegalSection title="Current status (honest language)">
        <p>Ember does not represent that it is HIPAA certified, and it does not currently advertise a
          standing, pre-signed BAA as a self-service feature. BAA terms, security review materials, and
          related compliance documentation are handled as a formal step of organization onboarding and the
          account/legal relationship, and can be reviewed and finalized at that time based on the
          organization's needs.</p>
      </LegalSection>

      <LegalSection title="BAA finalization as an onboarding / legal step">
        <p>If your organization requires a BAA, raise it during onboarding or through your account
          relationship so that appropriate terms can be reviewed and finalized. This avoids implying that a
          binding agreement is already in place before it has been executed by both parties.</p>
      </LegalSection>

      <LegalSection title="Organization responsibilities">
        <p>Organizations remain responsible for determining their HIPAA obligations, maintaining their own
          policies and safeguards, training staff, obtaining required client consents, and ensuring that any
          BAA in place reflects their actual use of the platform.</p>
      </LegalSection>

      <LegalSection title="42 CFR Part 2 sensitivity for SUD records">
        <p>Substance use disorder records are subject to additional protections under 42 CFR Part 2,
          including heightened consent requirements and restrictions on redisclosure. Organizations handling
          SUD records are responsible for applying these requirements in addition to HIPAA.</p>
      </LegalSection>

      <LegalDisclaimer>
        This page is provided for informational purposes only and does not constitute legal advice. It is
        not a Business Associate Agreement and does not create any binding obligation. Organizations should
        consult their own legal counsel regarding HIPAA, 42 CFR Part 2, and BAA requirements.
      </LegalDisclaimer>
    </LegalPageLayout>
  );
}
