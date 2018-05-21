import os 
import subprocess 
import numpy as np 
import sklearn.model_selection
import sklearn.metrics

import warnings 
warnings.filterwarnings('ignore')
    
class Suspect2Vec(object):

    def __init__(self, dim=20, epochs=4000, eta=0.01, lambd=None, train=0, verbose=False):
        '''
        parameters:
            dim: dimension of embeddings 
            epochs: Number of training epochs 
            eta: learning rate 
            train: Training scheme (0 for suspect subset, 1 for single suspects)
            lambd: regularization coefficient. If none do parameter search on validation data.             
        '''
        self._dim = dim 
        self._epochs = epochs 
        self._eta = eta 
        self._lambd = lambd 
        self._train = train
        self._dir_path = os.path.dirname(os.path.realpath(__file__))
        self._verbose = verbose 
        
        
    def _run_C_suspect2vec(self, one_hot_data, **args):
        m,n = one_hot_data.shape
        with open("in.txt","w") as f:
            f.write("%i %i\n" %(m,n))
            for row in one_hot_data:
                f.write(" ".join(map(str,map(int,row)))+"\n")
        
        params = {"epochs":self._epochs, "eta":self._eta, "lambd":self._lambd, "dim":self._dim, "train":self._train}
        for key in args:
            params[key] = args[key]
        cmd = "%s -in in.txt -out out.txt" %(os.path.join(self._dir_path,"suspect2vec"))
        for key in params:
            cmd += " -%s %s" %(key,params[key])
        stdout,stderr = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE).communicate()
        
        with open("out.txt") as f:
            self.embed_in = []
            self.embed_out = []
            for i in range(n):
                self.embed_in.append(list(map(float,f.readline().strip().split())))
            for i in range(n):
                self.embed_out.append(list(map(float,f.readline().strip().split())))
            self.embed_in = np.array(self.embed_in)            
            self.embed_out = np.array(self.embed_out)    
        assert not np.isnan(self.embed_in).any()
        assert not np.isnan(self.embed_out).any()

            
    def _validate(self, train_index, valid_index, lambd):
        self._run_C_suspect2vec(self.one_hot_data[train_index], lambd=lambd, epochs=1000)
        results = np.zeros(len(valid_index))
        for i,idx in enumerate(valid_index):
            sample = self.train_data[idx][:len(self.train_data[idx])/2] #self.train_data[idx] is actually validation data here 
            # TODO: get rid of all this unnecessary converting between suspects and ids
            sample = [self.suspect_union[s] for s in sample]
            pred = self.predict(sample)
            pred = [self.suspect2id[s] for s in pred]
            # print(pred)
            # print(sample)
            pred_1hot = np.zeros(len(self.one_hot_data[0]), dtype=np.bool_)
            pred_1hot[pred] = 1 
            metrics = sklearn.metrics.precision_recall_fscore_support(self.one_hot_data[idx], pred_1hot, labels=[0,1])
            results[i] = metrics[2][1]
        return np.mean(results)

             
    def fit(self, data):
        '''
        Learn the embed_in to predict suspect sets. 
        data: iterable of iterables of suspects
        '''        
        # preprocessing to convert suspects in data to integers from 0..n-1
        self.suspect_union = set([])
        for suspect_set in data:
            self.suspect_union = self.suspect_union.union(set(suspect_set))
        self.suspect_union = list(self.suspect_union)
        n = len(self.suspect_union)
        m = len(data)

        self.suspect2id = dict(zip(self.suspect_union, range(n)))

        self.train_data = []
        for S in data:
            self.train_data.append([self.suspect2id[s] for s in S])
        
        self.one_hot_data = np.zeros((m,n), dtype=np.bool_)
        for i in range(m):
            self.one_hot_data[i][self.train_data[i]] = 1
            
        if self._lambd is None:
            # Determine best value using validation data
            train_index,valid_index = sklearn.model_selection.train_test_split(range(m), test_size=0.25, random_state=1)
            val1 = self._validate(train_index, valid_index, 0.0)
            val2 = self._validate(train_index, valid_index, 0.1)
            if self._verbose:
                print("Validation results: 0.0 -> %.4f, 0.1 -> %.4f" %(val1,val2))
            self._lambd = 0.0 if val1 > val2 else 0.1 
        
        self._run_C_suspect2vec(self.one_hot_data)    
        return self.embed_in 
        
        
    def predict(self, sample, k=None):
        '''       
        Predict the remaiing suspects in the given suspect subset. 
        sample: iterable of suspects
        Returns: list of suspects
        '''
        n = len(self.suspect_union)
        ret = list(sample)
        sample = [self.suspect2id[s] for s in sample if s in self.suspect2id]
        sample_vec = np.mean(self.embed_in[sample], axis=0)
        scores = np.matmul(self.embed_out,sample_vec)
        
        if k is None:
            for i in range(n):
                if scores[i] > 0 and self.suspect_union[i] not in ret:
                    ret.append(self.suspect_union[i])
            return ret 
        else:
            # return ranking of all suspects by scores 
            suspect_scorez = []
            for i in range(n):
                suspect_scorez.append((scores[i],self.suspect_union[i]))
            suspect_scorez.sort()
            suspect_scorez.reverse()
            for s in suspect_scorez:
                if s[1] not in ret:
                    ret.append(s[1])
                    if len(ret) >= k:
                        break
            return ret 

            
    def get_embeddings(self):
        '''
        Return dict mapping suspects to embeddings for all known suspects.
        '''
        ret = {}
        for s in self.suspect_union:
            if s in self.suspect2id:
                ret[s] = self.embed_in[self.suspect2id[s]]
        return ret 
