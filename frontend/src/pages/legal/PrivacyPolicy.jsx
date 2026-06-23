import React from 'react';
import { Shield } from 'lucide-react';
import LegalPageLayout, { LegalSection, LegalDisclaimer } from '../../components/LegalPageLayout';

export default function PrivacyPolicy() {
  return (
    <LegalPageLayout
      icon={Shield}
      title="Privacy Policy"
      subtitle="How Ember handles information across the platform."
    >
      <LegalSection title="Summary">
        <p>
          Ember is a case management platform used by behavioral health, substance use disorder (SUD),
          reentry, and social services organizations. This policy explains, in plain language, what
          information the platform may collect, how it may be used, and the responsibilities that rest
          with the organizations who use it. Ember acts as a service provider to these organizations,
          which control the client and service data they enter.
        </p>
      </LegalSection>

      <LegalSection title="Information we may collect">
        <p><strong>Account and profile information.</strong> Names, work email addresses, organization or
          workspace details, role assignments, and authentication identifiers used to sign in and to apply
          role-based access.</p>
        <p><strong>Client and service documentation data.</strong> Information entered by authorized staff
          in the course of providing services — for example case notes, housing and benefits coordination,
          legal and FMLA tracking, treatment planning, and related documentation. This data is entered and
          owned by the organization that operates the workspace.</p>
        <p><strong>Usage and analytics data.</strong> Operational and product-analytics events (such as page
          visits and feature usage) used to keep the service running, troubleshoot issues, and improve the
          product. This is kept separate from clinical documentation wherever feasible.</p>
      </LegalSection>

      <LegalSection title="How information may be used">
        <p>To provide and operate the platform; to authenticate users and enforce role-based access; to
          support, maintain, secure, and improve the service; and to meet the organization's documented
          service needs. Ember does not sell personal information and does not use client/service
          documentation data for advertising.</p>
      </LegalSection>

      <LegalSection title="Data sharing limitations">
        <p>Information is shared only as needed to operate the service — for example with infrastructure and
          hosting providers that process data on Ember's behalf — or where required by law. Client and
          service data is not shared between organizations. Any AI-assisted features operate on data the
          organization has already entered and only to support that organization's own workflows.</p>
      </LegalSection>

      <LegalSection title="Organization responsibilities">
        <p>Organizations using Ember are responsible for determining the lawful basis for the data they
          collect, obtaining any required client consents or releases of information, configuring user
          access appropriately, training their staff, and maintaining their own internal privacy policies.
          Organizations decide which data is entered into the platform.</p>
      </LegalSection>

      <LegalSection title="Data retention and deletion requests">
        <p>Data is retained for as long as an organization maintains an active workspace or as needed to
          provide the service. Organizations may request export or deletion of their data; deletion requests
          are handled as part of the organization's account relationship and may be subject to legal or
          recordkeeping obligations that the organization itself is responsible for.</p>
      </LegalSection>

      <LegalSection title="Security overview">
        <p>Ember is designed with a secure-by-design posture, including authentication, role-based access,
          and data-minimization practices. Connections to the platform are served over encrypted transport
          (HTTPS/TLS) by our hosting providers. See the <a className="text-cyan-300 hover:text-white" href="/data-security">Data
          Security</a> page for more detail.</p>
      </LegalSection>

      <LegalSection title="Contact / support">
        <p>Signed-in users can reach the team through the in-app <strong>Help &amp; Support</strong> page,
          where a support ticket is the fastest way to reach us. Organization-level privacy questions can be
          raised with your organization administrator or during onboarding.</p>
      </LegalSection>

      <LegalDisclaimer>
        This Privacy Policy is provided for informational purposes only and does not constitute legal advice.
        Each organization is responsible for its own compliance obligations, internal policies, staff
        training, and configuration of the platform.
      </LegalDisclaimer>
    </LegalPageLayout>
  );
}
