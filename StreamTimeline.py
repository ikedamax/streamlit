# -*- coding: utf-8 -*-

import streamlit as st
from streamlit_timeline import timeline
import json
import base64
import magic
import os
import datetime
import pandas as pd
from PIL import Image
import redis, time


def image_to_uri(file_path):
    with open(file_path, "rb") as image_file:
        # bufに格納
        buf = image_file.read()
    
        # base64のdata取得
        data = base64.b64encode(buf)
        data_str = data.decode('utf-8')
    
        # MIMEタイプ取得
        mime_type = magic.from_buffer(buf, mime=True)
    
        # Data URI
        data_uri = "data:" + mime_type + ";base64," + data_str
    return data_uri

class StreamTimeline:

    def __init__(self):
        self.registered_entities = []

    def reset_timeline(self):
        with open(os.path.join(os.path.dirname(__file__), 'timeline_template.json'), "r") as f:
            timeline_data = json.load(f)
        with open(os.path.join(os.path.dirname(__file__), 'timeline.json'), "w", encoding="utf-8" ) as f:
            json.dump(timeline_data, f, indent=2, ensure_ascii=False)
        self.registered_entities = []
        self.registered_news = []

    def update_timeline(self, redis_server, time_commonsense, text_list=None, news_timeline=None, news_image_urls=None, time_commonsense_image_urls=None, dialog_turn_number=None):
        if not text_list:
            text_list = [""]*len(time_commonsense)
        if not time_commonsense_image_urls:
            time_commonsense_image_urls = [None] * len(time_commonsense)
        with open(os.path.join(os.path.dirname(__file__), 'timeline.json'), "r") as f:
            timeline_data = json.load(f)
        
        # 記憶を消すか
        timeline_data["events"] = []
        if news_timeline:
            self.update_news_timeline(redis_server, timeline_data, news_timeline, news_image_urls, dialog_turn_number=dialog_turn_number)
        # print(timeline_data)
        entity_dict = {}
        entity_dict["turn_"+str(dialog_turn_number)] = {}
        concept_net_dict = {}
        concept_net_dict["turn_"+str(dialog_turn_number)] = {}
        # if dialog_turn_number == 2:
        #     entity_dict[f'turn_{dialog_turn_number}'] = {'大切': '2022/01'}
        # elif dialog_turn_number!=1:
        #     entity_dict[f'turn_{dialog_turn_number}'] = {'記憶': '1980/01'}
        for time_table, texts, image_url in zip(time_commonsense, text_list, time_commonsense_image_urls):
            # print(time_table)
            if len(time_table) == 3:
                if texts == []:
                    texts == ""
                entity = time_table[0]
                # if entity in self.registered_entities:
                #     continue
                # self.registered_entities.append(entity)
                # if entity in timeline_data["events"]:
                #     continue
                start_date = time_table[1]
                end_date = time_table[2]
                event = {}
                if image_url:
                    event["media"]["url"] = image_url
                event["text"] = {"headline": entity, "text": str(texts)}
                event["start_date"] = {"year": start_date[0], "month":start_date[1]}
                event["end_date"] = {"year": end_date[0], "month":end_date[1]}
                timeline_data["events"].append(event)
                # print(timeline_data)
                # date = datetime.datetime(start_date[0], start_date[1])
                date = f"{start_date[0]}/{start_date[1]}"
                # entity_dict = redis_server.get_cli().hgetall("entity_time_table").items()
                # entity_dict = {k.decode("utf-8"): v.decode("utf-8") for k, v in entity_dict}
                # if not entity_dict:
                #     entity_dict = {}
                # # time_dict = {k.decode("utf-8"): eval(v.decode("utf-8")) for k, v in raw_time_dict}
                # # tmp = {}
                
                entity_dict["turn_"+str(dialog_turn_number)][entity] = date
                # entity_dict["entity_time_table"].append(tmp)
                if len(texts):
                    concept_net_dict["turn_"+str(dialog_turn_number)][entity] = str(texts)

                # concept_net_dict = redis_server.get_cli().hgetall("concept_net_table").items()
                # concept_net_dict = {k.decode("utf-8"): v.decode("utf-8") for k, v in concept_net_dict}
                # if not concept_net_dict:
                #     concept_net_dict = {}
                # if len(texts):
                #     concept_net_dict[entity] = str(texts)

        if len(entity_dict["turn_"+str(dialog_turn_number)]):
            print("entity_dict:", entity_dict)
            entity_dict["turn_"+str(dialog_turn_number)] = str(entity_dict["turn_"+str(dialog_turn_number)])
            redis_server.get_cli().hmset("entity_time_table", entity_dict)
        if len(concept_net_dict["turn_"+str(dialog_turn_number)]):
            concept_net_dict["turn_"+str(dialog_turn_number)] = str(concept_net_dict["turn_"+str(dialog_turn_number)])
            redis_server.get_cli().hmset("concept_net_table", concept_net_dict)

            
        with open(os.path.join(os.path.dirname(__file__), 'timeline.json'), "w", encoding="utf-8" ) as f:
            json.dump(timeline_data, f, indent=2, ensure_ascii=False)
        return timeline_data

    def update_personal_timeline(self, redis_server, personal_info:dict):
        with open(os.path.join(os.path.dirname(__file__), 'timeline_template.json'), "r") as f:
            timeline_data = json.load(f)
        timeline_data["title"]["text"]["text"] = str(personal_info)
        # for person_type, value in personal_info.items():
        #     timeline_data["title"]["text"]["text"].append(value)
        
        with open(os.path.join(os.path.dirname(__file__), 'timeline_template.json'), "w", encoding="utf-8" ) as f:
            json.dump(timeline_data, f, indent=2, ensure_ascii=False)
        return timeline_data

    def update_news_timeline(self, redis_server, timeline_data, news_timeline:dict, image_urls=None, dialog_turn_number=None):
        if not image_urls:
            image_urls = [None] * len(news_timeline)
        news_dict = {}
        news_dict["turn_"+str(dialog_turn_number)] = {}
        # if dialog_turn_number == 2:
        #     news_dict[f'turn_{dialog_turn_number}'] = {'2022-11-13': 'ロシア軍撤退で水力発電所やテレビ局施設を爆破か'}
        # elif dialog_turn_number!=1:
        #     news_dict[f'turn_{dialog_turn_number}'] = {'2022-02-27': '【速報】北朝鮮から発射された飛翔体はすでに落下か 日本政'}
        for (date, news), image_url in zip(news_timeline.items(), image_urls):
            # if news in self.registered_news:
            #     continue
            # self.registered_news.append(news)
            event = {}
            if image_url:
                event["media"] = {}
                event["media"]["url"] = image_url

            event["text"] = {"headline": news}
            date_ = date
            date = datetime.datetime.strptime(date, "%Y-%m-%d")
            event["start_date"] = {"year": date.year, "month": date.month, "day": date.day}
            event["end_date"] = {"year": date.year, "month": date.month, "day": date.day}
            timeline_data["events"].append(event)
            
            # news_dict[date_] = news
            news_dict["turn_"+str(dialog_turn_number)][date_] = news
            # if not news_dict:
            #     redis_server.get_cli().hmset("news_time_table", dict_)
                # news_dict["news_time_table"] = []
            # news_dict = {k.decode("utf-8"): eval(v.decode("utf-8")) for k, v in raw_news_dict}
            # tmp = {}
            # news_dict[date_] = news
            # news_dict["news_time_table"].append(tmp)
        if len(news_dict["turn_"+str(dialog_turn_number)]):
            # news_dict["news_time_table"] = news_dict
            news_dict["turn_"+str(dialog_turn_number)] = str(news_dict["turn_"+str(dialog_turn_number)])
            redis_server.get_cli().hmset("news_time_table", news_dict)
                    
        with open(os.path.join(os.path.dirname(__file__), 'timeline.json'), "w", encoding="utf-8" ) as f:
            json.dump(timeline_data, f, indent=2, ensure_ascii=False)
        return timeline_data
        
def main():
    # time.sleep(120)
    with open(os.path.join(os.path.dirname(__file__), 'redis_port.json'), "r") as f:
        redis_port = json.load(f)
    if redis_port["port"]:
        st.set_page_config(page_title="Timeline", layout="wide")
        redis_server = redis.Redis(host="localhost",port=redis_port["port"],db=0)

    # st.set_page_config(layout="wide")
    def init():
        st.markdown("## ユーザーの基本情報:")
        persona_info_tables = redis_server.hgetall("persona_info_tables")
        persona_info_tables = {k.decode("utf-8"): v.decode("utf-8") for k, v in persona_info_tables.items()}
        print(persona_info_tables)
        # persona = {'name': '池田寛人', 'gender': '男', 'age': 23, 'blood_type': 'B', 'birthday': datetime.date(1999, 11, 24), 'profession': '大学生', 'hobby': 'ツーリング'}
        df_s = pd.DataFrame(data=persona_info_tables, index=["基本情報"])
        st.write(df_s)

        st.markdown("## AIの性格:")
        # persona = {"問題回避": 0.1, "目的志向": 0.9, "内的基準": 0.3,  "外的基準": 0.7}
        # persona = {"問題回避": persona[0], "目的志向": persona[1], "内的基準": persona[2],  "外的基準": persona[3]}
        persona_info_tables = redis_server.hgetall("character_infos")
        persona_info_tables = {k.decode("utf-8"): v.decode("utf-8") for k, v in persona_info_tables.items()}
        print(persona_info_tables)
        # persona = {'name': '池田寛人', 'gender': '男', 'age': 23, 'blood_type': 'B', 'birthday': datetime.date(1999, 11, 24), 'profession': '大学生', 'hobby': 'ツーリング'}
        df_s = pd.DataFrame(data=persona_info_tables, index=["性格"])
        st.write(df_s)
        
        image = Image.open('character.png')
        st.image(image, caption='AIの性格',use_column_width=False, width=300)

        st.markdown("## AIの価値観:")
        # persona = {"問題回避": 0.1, "目的志向": 0.9, "内的基準": 0.3,  "外的基準": 0.7}
        # df_s = pd.DataFrame(data=persona, index=["基本情報"])
        st.markdown("- 一つのことを極める > いろいろやる")

    if redis_port["port"]:
        init()
        # st.markdown("## ユーザーの基本情報:")
        # persona_info_tables = redis_server.hgetall("persona_info_tables")
        # persona_info_tables = {k.decode("utf-8"): v.decode("utf-8") for k, v in persona_info_tables.items()}
        # print(persona_info_tables)
        # # persona = {'name': '池田寛人', 'gender': '男', 'age': 23, 'blood_type': 'B', 'birthday': datetime.date(1999, 11, 24), 'profession': '大学生', 'hobby': 'ツーリング'}
        # df_s = pd.DataFrame(data=persona_info_tables, index=["基本情報"])
        # st.write(df_s)

        # st.markdown("## AIの性格:")
        # # persona = {"問題回避": 0.1, "目的志向": 0.9, "内的基準": 0.3,  "外的基準": 0.7}
        # # persona = {"問題回避": persona[0], "目的志向": persona[1], "内的基準": persona[2],  "外的基準": persona[3]}
        # persona_info_tables = redis_server.hgetall("character_infos")
        # persona_info_tables = {k.decode("utf-8"): v.decode("utf-8") for k, v in persona_info_tables.items()}
        # print(persona_info_tables)
        # # persona = {'name': '池田寛人', 'gender': '男', 'age': 23, 'blood_type': 'B', 'birthday': datetime.date(1999, 11, 24), 'profession': '大学生', 'hobby': 'ツーリング'}
        # df_s = pd.DataFrame(data=persona_info_tables, index=["性格"])
        # st.write(df_s)
        
        # image = Image.open('character.png')
        # st.image(image, caption='AIの性格',use_column_width=False, width=300)

        # st.markdown("## AIの価値観:")
        # # persona = {"問題回避": 0.1, "目的志向": 0.9, "内的基準": 0.3,  "外的基準": 0.7}
        # # df_s = pd.DataFrame(data=persona, index=["基本情報"])
        # st.markdown("- 一つのことを極める > いろいろやる")


    with open(os.path.join(os.path.dirname(__file__), 'timeline.json'), "r") as f:
        data = f.read()

    # render timeline
    timeline(data, height=800)

    if redis_port["port"]:
        dialog_history = redis_server.hgetall("dialog_history")
        dialog_history = {k.decode("utf-8"): v.decode("utf-8") for k, v in dialog_history.items()}
        if len(dialog_history) % 2 == 0:
            dialog = list(dialog_history.values())
            for i in range(0, len(dialog), 2):
                message(dialog_history[f"user_utter_{i//2+1}"], key=str(i))
                # message(dialog[i], key=str(i))

                # init()
                # timeline(data, height=800)

                topic = redis_server.get(f"dialog_topic_{i//2+1}").decode("utf-8")
                topic_dict = {"現在の対話トピック": topic}
                df_s = pd.DataFrame(data=topic_dict, index=["トピック"])
                st.markdown("- 現在の対話トピック")
                st.write(df_s)
                emotion = redis_server.get(f"user_emotion_{i//2+1}").decode("utf-8")
                emotion_dict = {"内容の感情": emotion, "音声の感情": emotion, "見た目の感情": emotion}
                df_s = pd.DataFrame(data=emotion_dict, index=["感情"])
                st.markdown("- ユーザーの感情")
                st.write(df_s)
                # if i == 0:
                #     persona = {2020-4-5: "仕事で大きな失敗"}
                # else:
                #     persona = {2022-11-11: "ボランティア経験", 2020-4-5: "仕事で大きな失敗"}
                news_dict = redis_server.hgetall(f"news_time_table")
                news_dict = {k.decode("utf-8"): eval(v.decode("utf-8")) for k, v in news_dict.items() if int(k.decode("utf-8")[5:]) <= i//2+1}
                df_s = pd.DataFrame(data=list(news_dict.values()), index=list(news_dict.keys()))
                st.markdown("- 記憶")
                st.write(df_s)
                print("news_dict:", news_dict)

                entity_dict = redis_server.hgetall(f"entity_time_table")
                entity_dict = {k.decode("utf-8"): eval(v.decode("utf-8")) for k, v in entity_dict.items() if int(k.decode("utf-8")[5:]) <= i//2+1}
                print("entity_dict:", entity_dict)
                st.markdown("- 時系列")
                df_s = pd.DataFrame(data=list(entity_dict.values()), index=list(entity_dict.keys()))
                # df_s = pd.DataFrame(data=news_dict, index=["時系列"])
                st.write(df_s)

                concept_dict = redis_server.hgetall(f"concept_net_table")
                concept_dict = {k.decode("utf-8"): eval(v.decode("utf-8")) for k, v in concept_dict.items() if int(k.decode("utf-8")[5:]) <= i//2+1}
                st.markdown("- コンセプトネット")
                df_s = pd.DataFrame(data=list(concept_dict.values()), index=list(concept_dict.keys()))
                st.write(df_s)
                # print("concept_dict:", concept_dict)
                # persona = {"得る": "得る is get"}
                # df_s = pd.DataFrame(data=persona, index=["コンセプトネット"])
                # st.write(df_s)
                # message(dialog[i+1], is_user=True, key=str(i) + '_user')
                summarized_dict = redis_server.hgetall(f"summarized_utterance")
                summarized_dict = {k.decode("utf-8"): v.decode("utf-8") for k, v in summarized_dict.items() if int(k.decode("utf-8")[-1]) == i//2+1}
                print("summarized_dict", summarized_dict)
                df_s = pd.DataFrame(data=summarized_dict, index=["対話要約"])
                st.markdown("- 対話要約")
                st.write(df_s)
                message(dialog_history[f"system_utter_{i//2+1}"], is_user=True, key=str(i) + '_user')

        # persona = {"ボランティア": "ボランティア"}
        # df_s = pd.DataFrame(data=persona, index=["AIの知識"])
        # st.write(df_s)
if __name__ == '__main__':
    from streamlit_chat import message
    main()