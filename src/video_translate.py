import boto3
import requests
import re
from datetime import timedelta
import json


print('Loading function')
s3 = boto3.client(service_name= 's3',region_name='us-east-1')
bedrock = boto3.client(
    service_name='bedrock-runtime',
    region_name='us-east-1'
)

# object in s3://log-for-waf-cdn-handson/The.Vampire.Diaries.S01E01.ctu.chs.srt

source_lang = 'en'
target_lang = 'zh'
model_id = 'anthropic.claude-3-sonnet-20240229-v1:0'

def main():
    # Bucket Key from s3 event
    bucket = "log-for-waf-cdn-handson"
    key = "sample.srt"
    # region = os.environ['AWS_DEFAULT_REGION']
    # bucket_name = event['Records'][0]['s3']['bucket']['name']
    # sourceS3Key = event['Records'][0]['s3']['object']['key']

    # 从S3下载SRT文件
    #srt_content = download_srt_from_s3(bucket, key)
    input_file_name = key.split("/")[-1]
    print(input_file_name)
    local_input_file = "./" + input_file_name
    s3.download_file(bucket, key, local_input_file)

    # 解析SRT文件
    #srt_entries = parse_srt(srt_content)
    id_list, time_list, subtitles_list = read_srt(local_input_file)

    # 翻译文本
    translated_entries = translate_srt(subtitles_list,model_id,source_lang,target_lang)

    # 生成新的SRT文件内容
    new_srt_content = generate_srt(id_list, time_list,translated_entries)

    # 上传新的SRT文件到S3
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
        '''
        #with open(local_input_file, 'r', encoding='utf-8', errors='ignore') as f:
            srt_content = f.read()
        #srt_content = srt_obj['Body'].read().decode('utf-8')
        return srt_content
        
'''
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

def parse_srt(srt_content):
    entries = []
    entry_regex = re.compile(r'(\d+)\n(\d\d:\d\d:\d\d,\d\d\d --> \d\d:\d\d:\d\d,\d\d\d)\n(.*?)(?=\n\n|$)', re.DOTALL)
    for match in entry_regex.finditer(srt_content):
        index, timings, text = match.groups()
        start, end = [sum(x * int(t) for x, t in zip([3600, 60, 1], time.split(':'))) * 1000 for time in
                      timings.split(' --> ')]
        entries.append({'index': int(index), 'start': start, 'end': end, 'text': text.strip()})
    return entries


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
    '''
    for entry in translated_entries:
        start = str(timedelta(milliseconds=entry['start']))
        end = str(timedelta(milliseconds=entry['end']))
        srt_content += f"{entry['index']}\n{start.split('.')[0]},{start.split('.')[1]} --> {end.split('.')[0]},{end.split('.')[1]}\n{entry['text']}\n\n"
        '''
    return srt_content

if __name__ == '__main__':
    main()
