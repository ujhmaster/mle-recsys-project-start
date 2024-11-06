import pandas as pd
import logging

logging.basicConfig(filename='./logs/service.log',level=logging.INFO)

class RecRanks:

    def __init__ (self):
        """
        Класс RecRanks иницаализирует файл истории взаимодействия пользователя и информации о треках
        для каждого пользователя вычисляются веса предпочтений по жанрам, альбомам и исполнителям

        при поступлении оценки списка треклиста, возвращается сортированный список в зависимости от предпочтений пользователя
        """
        self._data = {
            "events": None, 
            "items" : None,
            }
        self._cache_user_weights = {}
        self.agg_filds = ['artists','albums','genres']
        
        self.load_rec_file(hendler='events',file_path='./data/events.parquet')
        self.load_rec_file(hendler='items',file_path='./data/items.parquet')

        logging.info(msg='Class ' + __name__ + ' init')
    
    def load_rec_file(self,hendler: str,file_path: str,**kwargs):
        """
        вызов функции позволяет обновить файл данных без повторной инициализации класса
        """
        self._data[hendler] = self.load_df(file_path=file_path,**kwargs)

    
    def load_df(self,file_path: str, **kwargs) -> pd.DataFrame:
        """
        Загрузчик данных из файла
        """
        try: 
            data = pd.read_parquet(path=file_path, **kwargs)
            logging.info(msg='Loaded seccessful from file: ' + file_path)
        except Exception as e:
            logging.error(msg=f"{file_path} {e}")

        return data
    
    def get_weights(self,user_id: int):
        """
        Возвращаем веса характеристик треков для пользователя
        """
        try:
            weights = self._cache_user_weights[user_id]
            logging.info(f"return chched weights ")
        except KeyError:
            weights =  self.calc_weights(user_id)
            logging.info(f"calc  ")
        except Exception as e:
            logging.error(f"personal_weights for user {user_id}: {e}")
            weights = self.zero_weights()

        return weights
    
    def calc_weights(self,user_id: int):
        """
        Вычисляем веса характеристик треков для пользователя
        """
        try:
            for_agg = self.agg_filds
            # выбираем треки с которыми взаимодействовал пользователь
            user_items = self._data['events'][self._data['events']['user_id'] == user_id][['user_id','item_id']]
            user_items = user_items.merge(self._data['items'][['item_id'] + for_agg],on='item_id')

            weights = {}
            for fild in for_agg:
                # количество прослушиваний с признаком
                calc_weight = user_items.explode(fild).groupby(fild).agg(score=(fild,"count"))
                # нормализация веса
                calc_weight['score'] = calc_weight['score'] / calc_weight['score'].sum()
                
                weights[fild] = calc_weight

            self._cache_user_weights[user_id] = weights
            logging.info(f"weights calculated for {user_id}")

        except Exception as e:
            logging.error(f"Error with weights for {user_id} ")
            weights = self.zero_weights()
            
        return weights
    
    def zero_weights():
        weights = {
                'genres': None,
                'artists': None,
                'albums': None
            }
        return weights

    
    def calc_ranks(self,user_id: int, item_ids: list):
        """
        взвешиваем треки из item_ids на веса пользователя user_id
        """
        weights = self.get_weights(user_id)
        items_for_rank = self._data['items'][self._data['items']['item_id'].isin(item_ids)]

        items_for_rank['score_total'] = 0
        for fild in self.agg_filds:
            if weights[fild] is not None:
                target_indexes = list(weights[fild].index)
                items_for_rank['score_' + fild] = [weights[fild].loc[x].sum()['score'] if set(x).issubset(target_indexes) else 0 for x in items_for_rank[fild]]
                items_for_rank['score_total'] += items_for_rank['score_' + fild]

        recs_df = items_for_rank.sort_values(by='score_total',ascending=False)
        recs = recs_df['item_id'].to_list()

        return recs

