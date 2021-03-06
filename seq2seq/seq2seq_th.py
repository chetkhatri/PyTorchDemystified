import random

import torch
import torch.nn as nn
from torch.autograd import Variable
from torch import optim
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np

from util import get_data


"""
get_data returns objects with
        id2vocab: dict{int:char}
        vocab2id: dict{char:int}
        text: list[str]
        text_as_ids: list[list[int]]
"""
en, fr = get_data()

use_cuda = torch.cuda.is_available()
epochs = 30
hidden_size = 512
embedding_size = 300
num_layers = 1
lr = 0.001
sent_len = len(en.text_as_ids)
n_iter = 500


class EncoderNetowrk(nn.Module):
    """
    Encoder network with embedding and GRU layer
    param: vocab_size
    param: hidden_size
    param: embedding_size -> size of embedding vector (300 normally)
    param: num_layers
    """

    def __init__(self, vocab_size, hidden_size, embedding_size, num_layers=1):
        super().__init__()
        self.embed = nn.Embedding(vocab_size, embedding_size)
        self.gru = nn.GRU(embedding_size, hidden_size, num_layers)

    def forward(self, inputs, hidden):
        embedded = self.embed(inputs)
        outputs, hidden = self.gru(embedded, hidden)
        return outputs, hidden


class DecoderNetwork(nn.Module):
    """
    Decoder network with embedding, GRU and fullyconnected Softmax layer
    param: vocab_size
    param: hidden_size
    param: embedding_size -> size of embedding vector (300 normally)
    param: num_layers
    """

    def __init__(self, vocab_size, hidden_size, embedding_size, num_layers=1):
        super().__init__()
        self.embed = nn.Embedding(vocab_size, embedding_size)
        self.gru = nn.GRU(embedding_size, hidden_size, num_layers)
        self.fc = nn.Linear(hidden_size, vocab_size)
        self.softmax = nn.LogSoftmax()

    def forward(self, inputs, hidden):
        embedded = self.embed(inputs)
        outputs, hidden = self.gru(embedded, hidden)
        outputs = self.softmax(self.fc(outputs[0]))
        return outputs, hidden


def get_batches(n_iter):
    for _ in range(n_iter):
        i = random.randint(0, sent_len - 1)
        enc_inputs = en.text_as_ids[i]
        dec_inputs = [fr.vocab2id['<GO>']] + fr.text_as_ids[i]
        dec_outputs = fr.text_as_ids[i] + [fr.vocab2id['<EOS>']]
        yield enc_inputs, dec_inputs, dec_outputs


def showPlot(points):
    plt.figure()
    fig, ax = plt.subplots()
    # this locator puts ticks at regular intervals
    loc = ticker.MultipleLocator(base=0.2)
    ax.yaxis.set_major_locator(loc)
    plt.plot(points)


encoder = EncoderNetowrk(len(en.id2vocab), hidden_size, embedding_size).cuda()
decoder = DecoderNetwork(len(fr.id2vocab), hidden_size, embedding_size).cuda()

print(decoder)

# Training
encoder_optim = optim.SGD(encoder.parameters(), lr=lr)
decoder_optim = optim.SGD(decoder.parameters(), lr=lr)
criterion = nn.NLLLoss()
loss2plot = []


for epoch in range(epochs):
    for enc_inputs, dec_inputs, dec_outputs in get_batches(n_iter):
        accuracy = []
        encoder_optim.zero_grad()
        decoder_optim.zero_grad()
        loss = 0
        hidden_state = Variable(torch.zeros(1, 1, hidden_size)).cuda()
        for val in enc_inputs:
            var = Variable(torch.LongTensor([[val]])).cuda()
            output, hidden_state = encoder(var, hidden_state)
        for i in range(len(dec_inputs)):
            var = Variable(torch.LongTensor([[dec_inputs[i]]])).cuda()
            output, hidden_state = decoder(var, hidden_state)
            value, index = output.topk(1)
            pred = index.data[0][0]
            accuracy.append(pred == dec_outputs[i])
            loss += criterion(output[0], Variable(torch.LongTensor([dec_outputs[i]])).cuda())
        outaccu = np.mean(accuracy)
        loss2plot.append(loss.data[0] / len(dec_inputs))
        outloss = np.mean(loss2plot)
        # TensorBoard integration, Import the TF logger file first
        # train_tf_logger.log(step=len(loss2plot), accuracy=outaccu, loss=outloss)
        loss.backward()
        encoder_optim.step()
        decoder_optim.step()
        # loss2plot has total iterations
        if len(loss2plot) % 50 == 0:
            print(
                'Epoch: {}, Iteration: {}, Loss: {}, min_loss: {}'.format(
                    epoch, len(loss2plot) % n_iter, loss.data[0] / len(dec_inputs), min(loss2plot)))
    # showPlot(loss2plot)

# Inference
enc_inputs, dec_inputs, dec_outputs = get_batches(n_iter).__next__()
hidden_state = Variable(torch.zeros(1, 1, hidden_size)).cuda()
for val in enc_inputs:
    var = Variable(torch.LongTensor([[val]])).cuda()
    output, hidden_state = encoder(var, hidden_state)
output = Variable(torch.LongTensor([[fr.vocab2id['<GO>']]])).cuda()
prediction = []
while True:
    output, hidden_state = decoder(output, hidden_state)
    value, index = output.topk(1)
    pred = index.data[0][0]
    if pred == fr.vocab2id['<EOS>'] or len(prediction) == 20:
        break
    else:
        prediction.append(pred)
        output = Variable(torch.LongTensor([[pred]])).cuda()
predicted_sent = ' '.join([fr.id2vocab[val] for val in prediction])
original_sent = ' '.join([en.id2vocab[val] for val in enc_inputs])
print(original_sent)
print(predicted_sent)

# Let's say we need to print the Loss function and see whats happening
# Just as you thought, you can do it
# loss getting converted from int to Variable
# Comparision op with variable and int
