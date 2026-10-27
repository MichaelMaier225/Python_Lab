from django.contrib.auth.tokens import PasswordResetTokenGenerator

class VerificationTokenGenerator(PasswordResetTokenGenerator):
    key_salt = "commerce.email-verification"

    def _make_hash_value(self, user, timestamp):
        return super()._make_hash_value(user, timestamp) + str(user.is_active)

verification_token = VerificationTokenGenerator()
