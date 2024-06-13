import boto3
import json
import re

print('Loading function')
s3 = boto3.client('s3')
bedrock = boto3.client(
    service_name='bedrock-runtime',
    region_name='us-east-1'
)

source_lang = 'en'
target_lang = 'zh'
model_id = 'anthropic.claude-3-sonnet-20240229-v1:0'


def lambda_handler(event, context):
    # Bucket Key from s3 event
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']
    #region = os.environ['AWS_DEFAULT_REGION']


    # download file
    input_file_name = key.split("/")[-1]
    print(input_file_name)
    local_input_file = "/tmp/" + input_file_name
    s3.download_file(bucket, key, local_input_file)

    # read file content
    id_list, time_list, subtitles_list = read_srt(local_input_file)

    # translate with claude3
    translated_entries = translate_srt(subtitles_list,model_id,source_lang,target_lang)

    # merge new file
    new_srt_content = generate_srt(id_list, time_list,translated_entries)

    # upload new file
    new_key = key.replace('.srt', '_translated.srt')
    s3.put_object(Bucket=bucket, Key=new_key, Body=new_srt_content.encode('utf-8'))

    return {
        'statusCode': 200,
        'body': f'Translated SRT file uploaded to {bucket}/{new_key}'
    }


def download_srt_from_s3(bucket, key):

    try:
        input_file_name = key.split("/")[-1]
        print(input_file_name)
        local_input_file = "./" + input_file_name
        s3.download_file(bucket, key, local_input_file)
    except Exception as e:
        print(f"Error downloading SRT file from S3: {e}")
        raise e
    
def read_srt(filename):
    id_list = []
    time_list = []
    subtitles_list = []
    with open(filename, encoding='utf-8') as srt_file:
        content = srt_file.read()
        content_split = content.split("\n\n")
        #print(content_split)
        for one_content in content_split:
            if one_content != '':
                id_list.append(one_content.split("\n")[0])
                time_list.append(one_content.split("\n")[1])
                subtitles_list.append(one_content.split("\n")[2:])
    return id_list, time_list, subtitles_list

def translate_srt(srt_entries,model_id,source_lang,target_lang):
    translated_entries = []
    model_id = model_id
    max_tokens = 50000
    system = "You are a skilled television drama subtitle translator proficient in multiple languages, your need to translate subtitles from the original video into the specified language."
    for entry in srt_entries:
        text = '\n'.join(entry)
        #print(text)
        if text:
            prompt = f"""Please follow the rules in translation:
            1. Keep the style of the original film and restore the meaning of the original words.
            2. Avoid "English Chinese" in the translation.
            3. Avoid "wordiness".
            4. The translation should reduce "cultural interference".
            5. Keep sentences as simple as possible.
            6. Maintain consistency with the personal pronoun used in the previous translation. Do not add a personal pronoun even if the grammatical is incorrect.
            Translate text in <subtitles> from <source_lang> into <target_lang>,keep a very authentic and popular tone:
            <subtitles>{text}</subtitles>
            <source_lang>{source_lang}</source_lang> 
            <target_lang>{target_lang}</target_lang>
            Put response only translation result and do not include any extra content.
             """
            message = {"role": "user", "content": [{"type": "text", "text": prompt}]}
            messages = [message]

            body = json.dumps(
                {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": max_tokens,
                    "system": system,
                    "messages": messages,
                    "temperature": 0.2,
                    "top_p": 0.999,
                    "top_k": 250
                }
            )

            response = bedrock.invoke_model(body=body, modelId=model_id)
            response_body = json.loads(response.get('body').read())
            response_text = response_body['content'][0]['text']
            #translated_text = response.json()['translation']
            translated_entries.append(response_text)

    return translated_entries

def generate_srt(id_list, time_list,translated_entries):
    srt_content = ''
    for i in range(len(id_list)):
        srt_content = srt_content + id_list[i] + "\n" + time_list[i] + "\n" + translated_entries[i] + "\n\n"
    return srt_content


