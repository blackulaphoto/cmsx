import React from 'react';
import { Lock } from 'lucide-react';
import LegalPageLayout, { LegalSection, LegalDisclaimer } from '../../components/LegalPageLayout';

export default function DataSecurity() {
  return (
    <LegalPageLayout
      icon={Lock}
      title="Data Security"
      subtitle="Ember's approach to protecting platform data."
    >
      <LegalSection title="Summary">
        <p>
          Ember is built with a secure-by-design posture appropriate for organizations handling sensitive
          behavioral health, SUD, and social services information. This page describes our current security
          approach in conservative, honest terms. It does not assert any third-party certification.
        </p>
      </LegalSection>

      <LegalSection title="Secure-by-design posture">
        <p>Security is considered throughout the platform's design — including how users authenticate, how
          access is scoped, and how sensitive data is handled and minimized.</p>
      </LegalSection>

      <LegalSection title="Authentication and role-based access">
        <p>Access requires authentication, and the platform applies role-based access controls so users see
          functionality and data appropriate to their role. Organization administrators manage their own
          users and role assignments.</p>
      </LegalSection>

      <LegalSection title="Data minimization">
        <p>The platform is designed to collect and surface the information needed to support service
          delivery. Product analytics are kept separate from clinical documentation wherever feasible.</p>
      </LegalSection>

      <LegalSection title="Auditability and logging">
        <p>The platform records administrative and key activity events to support accountability and review
          where currently supported. Logging coverage continues to expand as the product matures.</p>
      </LegalSection>

      <LegalSection title="Encryption in transit">
        <p>Connections to Ember are served over encrypted transport (HTTPS/TLS) by our hosting providers.
          Additional storage-level protections depend on the capabilities of our infrastructure providers;
          specific encryption-at-rest guarantees can be reviewed as part of security due diligence during
          onboarding.</p>
      </LegalSection>

      <LegalSection title="Incident response posture">
        <p>In the event of a suspected security incident, Ember's approach is to investigate promptly, take
          reasonable steps to contain and remediate, and communicate with affected organizations as
          appropriate. Organizations are responsible for their own internal incident-response obligations
          and any required notifications.</p>
      </LegalSection>

      <LegalSection title="Vendor and integration responsibility">
        <p>Ember relies on infrastructure and hosting providers to operate the service, and may connect to
          third-party integrations that an organization chooses to enable. Organizations are responsible for
          reviewing and accepting the terms and security posture of any integrations they turn on.</p>
      </LegalSection>

      <LegalSection title="Administrative safeguards">
        <p>Organizations remain responsible for administrative safeguards within their own operations —
          including staff onboarding and offboarding, password hygiene, device security, and internal
          policies governing how the platform is used.</p>
      </LegalSection>

      <LegalSection title="Security review readiness">
        <p>Ember can provide security overview materials and participate in an organization's security
          review or due-diligence process during onboarding. We do not currently claim any formal
          certification such as SOC 2, HITRUST, or ISO 27001.</p>
      </LegalSection>

      <LegalDisclaimer>
        This page is provided for informational purposes only and does not constitute legal advice or a
        warranty of security outcomes. Each organization is responsible for its own security policies,
        configuration, staff training, and compliance obligations.
      </LegalDisclaimer>
    </LegalPageLayout>
  );
}
