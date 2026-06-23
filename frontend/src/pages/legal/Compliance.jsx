import React from 'react';
import { ClipboardCheck } from 'lucide-react';
import LegalPageLayout, { LegalSection, LegalDisclaimer } from '../../components/LegalPageLayout';

export default function Compliance() {
  return (
    <LegalPageLayout
      icon={ClipboardCheck}
      title="Compliance"
      subtitle="How Ember supports compliance-oriented workflows."
    >
      <LegalSection title="Summary">
        <p>
          Ember is designed to support compliance-oriented workflows for organizations in behavioral health,
          SUD, reentry, and social services. Importantly, using Ember does not, by itself, make an
          organization compliant — compliance is achieved through an organization's own policies, training,
          consents, and operational practices, supported by the tools Ember provides.
        </p>
      </LegalSection>

      <LegalSection title="HIPAA-aware workflows">
        <p>The platform is designed with HIPAA-aware workflows in mind, including authentication, role-based
          access, and documentation practices intended to support the confidentiality of protected health
          information. Ember does not claim to be HIPAA certified, and no such certification exists for
          software products.</p>
      </LegalSection>

      <LegalSection title="42 CFR Part 2-aware workflows for SUD records">
        <p>Because many organizations handle substance use disorder records, the platform is designed to be
          aware of the heightened sensitivity of these records under 42 CFR Part 2, including the importance
          of consent and restrictions on redisclosure. Organizations remain responsible for applying Part 2
          requirements to their own programs.</p>
      </LegalSection>

      <LegalSection title="Role-based access">
        <p>Access is scoped by role so that staff can work with the information appropriate to their
          responsibilities. Organization administrators control role assignments.</p>
      </LegalSection>

      <LegalSection title="Minimum necessary principle">
        <p>The platform is designed to support the minimum-necessary principle by surfacing the information
          needed for a task and applying role-based access to limit broader exposure.</p>
      </LegalSection>

      <LegalSection title="Documentation support">
        <p>Ember provides structured documentation, templates, and tracking that can support an
          organization's recordkeeping and review processes.</p>
      </LegalSection>

      <LegalSection title="Consent and releases of information">
        <p>Consent and release-of-information (ROI) practices are central to lawful information sharing,
          particularly for SUD records. Organizations are responsible for obtaining, recording, and honoring
          the consents and releases required for their work.</p>
      </LegalSection>

      <LegalSection title="Audit and review support">
        <p>The platform records administrative and key activity events where currently supported, which can
          assist organizations with internal audit and review.</p>
      </LegalSection>

      <LegalSection title="Organization policy responsibility">
        <p>Each organization is responsible for its own compliance program — including written policies,
          workforce training, access governance, breach procedures, and any required agreements with
          partners and vendors.</p>
      </LegalSection>

      <LegalSection title="What Ember does and does not do">
        <p>Ember supports compliance workflows and provides tooling to help organizations operate
          responsibly. Ember does not make an organization compliant on its own, and does not provide legal
          or regulatory advice. See the <a className="text-cyan-300 hover:text-white" href="/hipaa-baa">HIPAA /
          BAA</a> page for more on business associate considerations.</p>
      </LegalSection>

      <LegalDisclaimer>
        This page is provided for informational purposes only and does not constitute legal or compliance
        advice. Organizations are solely responsible for determining and meeting their own compliance
        obligations.
      </LegalDisclaimer>
    </LegalPageLayout>
  );
}
