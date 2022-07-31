# 음성 텍스트 변환
import speech_recognition as sr
import pyaudio

# 형태소 분석
from konlpy.tag import Okt
import pandas as pd
okt = Okt()

# 인식할 수 없는 형태의 음원 파일을 변환하기 위한 모듈
from pydub import AudioSegment

# 데이터프레임 출력을 위한 모듈
from IPython.display import display

# wav 파일 길이를 가져오기
import wave
import contextlib

# 생성된 wav 파일을 지우기 위한 모듈
import os

class voice:    
    def __init__(self, input_file):
        self.file = input_file   # 분석을 원하는 음성 파일
        self.r = sr.Recognizer() 
        
        self.df = pd.read_csv("500_가중치.csv", encoding='utf-8')             # 전체 형태소 분석 (가중치) 파일 
        self.type_df = pd.read_csv("type_token_가중치.csv", encoding='utf-8') # 범죄 유형 분류 기준 단어 파일
        
        self.cnt = 1        # 보이스피싱 확률 변수
        self.type1_cnt = 1  # 대출사기형 확률
        self.type2_cnt = 1  # 수사기관사칭형 확률        
        self.text = ''      # 음성에서 변환된 텍스트
        self.export_cnt = 0 # 새롭게 wav 파일이 만들어졌는지 여부를 알기 위함
        
    # 음성 파일을 wav 파일로 통일하는 함수
    def to_wav(self):
        try:
            if self.file[self.file.rfind('.')+1:] != 'wav':
                sound = AudioSegment.from_file(self.file) 
                self.file = self.file[:self.file.rfind('.')]+'.wav'
                sound.export(self.file , format="wav")  # 파일을 인식할 수 있도록 파일 형식 변환
                self.export_cnt = 1
            
            with contextlib.closing(wave.open(self.file,'r')) as f:
                frames = f.getnframes()
                rate = f.getframerate()
                duration = frames / float(rate)
                
            self.duration_list = [30]*int(duration/30) + [round(duration%30)]
                
        except:
            print('Error')
            
    # 음성을 텍스트로 변환하는 함수        
    def recognize(self):
        try:
            with sr.AudioFile(self.file) as source:
                for duration in self.duration_list:
                    self.r.adjust_for_ambient_noise(source, duration=0.5)
                    self.r.dynamic_energy_threshold = True
                    audio = self.r.record(source, duration=duration)
                    try:
                        self.text += self.r.recognize_google(audio_data=audio, language='ko-KR')
                    except:
                        None
                
            #print(self.text)
            
            if self.export_cnt == 1:
                if os.path.exists(self.file):
                    os.remove(self.file)
                    
        except: 
            print('Error')
            
    # 텍스트 파일을 형태소 분석하는 코드
    def detection(self):
        self.token_ko = pd.DataFrame(okt.pos(self.text), columns=['단어', '형태소'])
        self.token_ko = self.token_ko[(self.token_ko['단어'].str.len() > 1)&(self.token_ko.형태소.isin(['Noun', 'Adverb']))]

        token_dict = {} # 단어:횟수 딕셔너리 생성
            
        for i in self.token_ko.단어.values:
            if i in self.df.단어.values:
                self.cnt *= float(self.df.loc[self.df.단어==i, '확률'])
                if i not in token_dict:
                    token_dict[i] = 1
                else:
                    token_dict[i] = token_dict.get(i) + 1 

        self.token_df = pd.DataFrame(zip(token_dict.keys(),token_dict.values()), columns=['의심 단어', '횟수'])
        self.token_df = self.token_df.sort_values(by='횟수', ascending=False)
    
        if self.cnt > 100:
            self.cnt = 100  # 확률이 100%를 넘겼을 경우 100으로 초기화
            
    # 유형을 분류하는 함수 
    def categorizing(self):
        for i, x in zip(self.token_df['의심 단어'].values, self.token_df['횟수'].values):
            if i in self.type_df.type1_단어.values:
                self.type1_cnt *= float(self.type_df.loc[self.type_df.type1_단어==i, 'type1_확률']) ** x
            elif i in self.type_df.type2_단어.values:
                self.type2_cnt *= float(self.type_df.loc[self.type_df.type2_단어==i, 'type2_확률']) ** x
                
        if self.type1_cnt > self.type2_cnt:
            return '대출사기형'
        else:
            return '수사기관사칭형'
                        
    # 결과를 출력하는 함수
    def result(self):
        self.to_wav()
        self.recognize() # 음성 텍스트 변환 함수 호출
        self.detection() # 분석 함수 호출
        
        if self.cnt <= 20: safe_type = '안전'
        elif self.cnt <= 40: safe_type = '의심'
        elif self.cnt <= 60: safe_type = '경고'
        else: safe_type = '위험'
            
        bolded_safe_type = "\033[1m" + safe_type + "\033[0m"
            
        print(f'▶ 보이스피싱 확률 : {self.cnt:.2f}% [{bolded_safe_type}]')
        
        # 보이스피싱 확률이 의심 단계 이상일 때만 출력할 수 있도록 함
        if self.cnt > 20:
            self.token_csv = self.token_ko['단어'].values # csv 생성을 위한 통화음성 단어 추출 (명사, 부사)
            
            type_title = self.categorizing() # 유형 분류 함수 호출
            #print(f'▶ 해당 음성은 {type_title} 보이스피싱일 가능성이 높습니다')
            #print('▶ 보이스피싱 탐색 결과')
            #display(self.token_df.head(10))
            