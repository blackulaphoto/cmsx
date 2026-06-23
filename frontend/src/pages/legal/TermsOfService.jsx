import React from 'react';
import { ScrollText } from 'lucide-react';
import LegalPageLayout, { LegalSection, LegalDisclaimer } from '../../components/LegalPageLayout';

export default function TermsOfService() {
  return (
    <LegalPageLayout
      icon={ScrollText}
      title="Terms of Service"
      subtitle="The terms that govern use of the Ember platform."
    >
      <LegalSection title="Summary">
        <p>
          These terms govern access to and use of Ember by organizations and their authorized staff. Ember
          is a professional case management tool for behavioral health, SUD, reentry, and social services
          work. It is not an emergency service and does not provide legal or medical advice.
        </p>
      </LegalSection>

      <LegalSection title="Acceptance of terms">
        <p>By accessing or using Ember, the organization and its users agree to these terms. If you do not
          agree, do not use the platform.</p>
      </LegalSection>

      <LegalSection title="Intended users">
        <p>Ember is intended for use by authorized staff of organizations that provide case management and
          related social services. It is a professional tool and is not intended for direct use by clients
          or the general public.</p>
      </LegalSection>

      <LegalSection title="Organization account responsibility">
        <p>Each organization is responsible for the activity that occurs under its workspace, for managing
          its users and their roles, for keeping credentials secure, and for the accuracy and lawfulness of
          the data it enters.</p>
      </LegalSection>

      <LegalSection title="Appropriate use">
        <p>Users agree to use Ember only for legitimate service-delivery purposes, to access only the data
          they are authorized to access, and not to misuse, disrupt, reverse engineer, or attempt to gain
          unauthorized access to the platform.</p>
      </LegalSection>

      <LegalSection title="Not a replacement for emergency or crisis services">
        <p><strong>Ember is not an emergency or crisis response system.</strong> It must not be relied upon
          in situations involving immediate risk of harm. In an emergency, contact 911 or the appropriate
          local emergency or crisis services (for example, 988 in the United States).</p>
      </LegalSection>

      <LegalSection title="No legal or medical advice">
        <p>Content within the platform — including AI-assisted suggestions, templates, and documentation
          aids — is provided to support professional workflows and does not constitute legal, medical, or
          clinical advice. Professional judgment and applicable standards of care always govern.</p>
      </LegalSection>

      <LegalSection title="User responsibilities">
        <p>Users are responsible for maintaining the confidentiality of their credentials, for following
          their organization's policies and applicable law, for obtaining any required client consents, and
          for the content they create or upload.</p>
      </LegalSection>

      <LegalSection title="Service availability">
        <p>Ember aims to provide reliable access but does not guarantee uninterrupted or error-free service.
          Maintenance, updates, and factors outside our control may affect availability.</p>
      </LegalSection>

      <LegalSection title="Intellectual property">
        <p>The Ember platform, including its software, design, and branding, is owned by Ember and its
          licensors. Organizations retain ownership of the client and service data they enter.</p>
      </LegalSection>

      <LegalSection title="Limitation of liability">
        <p>To the maximum extent permitted by law, Ember is provided "as is" without warranties of any kind,
          and Ember is not liable for indirect, incidental, or consequential damages arising from use of the
          platform. Organizations remain responsible for their own service delivery and compliance.</p>
      </LegalSection>

      <LegalSection title="Changes to the service or these terms">
        <p>Ember may update the platform and these terms over time. Material changes will be reflected by an
          updated "last updated" date, and continued use after changes constitutes acceptance.</p>
      </LegalSection>

      <LegalDisclaimer>
        These Terms of Service are provided for informational purposes only and do not constitute legal
        advice. Organizations are responsible for their own compliance obligations, internal policies, staff
        training, and configuration.
      </LegalDisclaimer>
    </LegalPageLayout>
  );
}
