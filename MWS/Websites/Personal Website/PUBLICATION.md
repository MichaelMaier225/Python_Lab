# Owner publication notes

The website can be hosted as static files without a build. This revision is for review in GitHub; pushing does not establish that the deployed website has updated.

## Policies and project agreements

Public navigation uses normal policy labels rather than draft labels. The policy text has not received legal review. Review the service terms, cancellation/refund language, ownership/licensing provisions and privacy notice before publishing. Use a written agreement for every project. The legacy `Client_Agreement_Template.txt` concerns website services and is not the new data-services agreement.

Before project data is shared, document the agreed transfer method, necessary data, authorized access, retention period, deletion procedure and provider/backup limitations. Do not promise security controls that have not been verified. No customer datasets may be used for model training without explicit authorization.

## Contact and payments

Direct email and telephone retain the original business contact details. The optional guided request prepares an email for the visitor to send. There is no server submission, payment processor or upload service. A true submission form requires a configured delivery provider, server-side validation, spam/rate controls, error handling and a retention policy; it is not represented as implemented.

Confirm contact details and test email handoff on the deployed site. Confirm payment arrangements in the quote; no payment-method claims were added.

## Offer and deployment

Confirm the founding offer against business records. Change `foundingOffer.enabled` in `site-config.js` to close it. The website does not infer a remaining-spots count.

Upload the complete website directory, including `mws.css`, `mws.js`, `demos.js` and `site-config.js`, preserving relative paths. Old demo URLs are forwarding pages. Verify HTTPS, host security settings and live links on the actual host. Root `render.yaml` belongs to the separate Sacratissimum application.
