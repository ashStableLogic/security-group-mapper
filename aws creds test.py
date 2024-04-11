from getpass import getpass
# from aws_sessions import AwsSession

aws_access_key_id=getpass('aws_access_key_id: ')
aws_secret_access_key=getpass('aws_secret_access_key: ')
aws_session_token=getpass('aws_session_token (for temporary credentials): ')

# AwsSession.set_creds(
#     aws_access_key_id,
#     aws_secret_access_key,
#     aws_session_token
# )