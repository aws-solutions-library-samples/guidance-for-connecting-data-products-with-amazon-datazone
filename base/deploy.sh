UUID_ENV=$(uuidgen)
UUID_ENV=${UUID_ENV:0:7}
UUID_ENV=$(echo $UUID_ENV | tr '[:upper:]' '[:lower:]')
BUCKET_NAME="cfn-dz-conn-base-env-${UUID_ENV}"

while getopts p:a: flag
do
    case "${flag}" in
        p) PROFILE_NAME=${OPTARG};;
        a) ACCOUNT_ID=${OPTARG};;
    esac
done

aws cloudformation deploy --stack-name dz-conn-base-env --template-file base/template.yaml --parameter-overrides "file://base/params/dz_conn_b_${ACCOUNT_ID}_params.json" --capabilities  CAPABILITY_NAMED_IAM --profile $PROFILE_NAME