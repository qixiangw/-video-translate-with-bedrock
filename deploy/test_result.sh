#!/bin/bash
if [ "$#" -ne 1 ];then
    echo "Please input s3 bucket name!"
    exit 1
else
    s3_bucket=${1}
 
    sudo yum install mkfontscale fontconfig freetype glibc gcc gcc-c++ autoconf automake libtool wget git  -y
    cd /usr/local/bin 
    sudo wget https://johnvansickle.com/ffmpeg/builds/ffmpeg-git-amd64-static.tar.xz && sudo tar -xvf ffmpeg-git-amd64-static.tar.xz 
    sudo ln -s /usr/local/bin/ffmpeg-git-20240629-amd64-static/ffmpeg /usr/bin/ffmpeg
    mkdir /home/cloudshell-user/translate && cd /home/cloudshell-user/translate && git clone https://github.com/qixiangw/video-translate-with-bedrock.git
    sudo cp video-translate-with-bedrock/resource/fonts/ZhuqueFangsong-Regular.ttf   /usr/share/fonts/
    sudo cd /usr/share/fonts/ && sudo mkfontscale

    cd /home/cloudshell-user/translate/video-translate-with-bedrock/resource/
    aws s3 cp s3://${s3_bucket}/output/input_translated.srt .
    ffmpeg -i input.mp4 -vf "subtitles=input_translated.srt:force_style='Zhuque Fangsong (technical preview),朱雀仿宋（预览测试版）'" -c:a copy output.mp4
    aws cp s3 output.mp4 s3://${s3_bucket}/output/output.mp4 

fi



    #将翻译后的字幕下载到本地，并与本地的视频结合后上传
