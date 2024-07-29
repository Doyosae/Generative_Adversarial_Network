# -*- coding: utf-8 -*-
"""tf.layers DCGAN with MNIST.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1RAyuWGghiEycnT9mySWKY_K7AMDPqEjd
"""

import os, ssl
if (not os.environ.get('PYTHONHTTPSVERIFY', '') and
    getattr(ssl, '_create_unverified_context', None)): 
    ssl._create_default_https_context = ssl._create_unverified_context

import numpy as np
import tensorflow as tf
import matplotlib.pyplot as plt
 
from tensorflow.examples.tutorials.mnist import input_data
mnist = input_data.read_data_sets("./mnist/data/", one_hot=True)


# Generator Function
def Build_Generator (inputs):
    
    # 이하 Generator 관여하는 모든 변수는 variable_scope로 묶어요.
    with tf.variable_scope("GeneratorVal"):
        
        output = tf.layers.dense(inputs, 128*7*7)
        output = tf.reshape(output, [-1, 7, 7, 128])
        output = tf.layers.batch_normalization(output, training = IsTraining)
        output = tf.nn.relu (output)
        
        output = tf.layers.conv2d_transpose(output, 64, [5, 5], strides = (2, 2), padding = "SAME", use_bias = False)
        output = tf.layers.batch_normalization(output, training = IsTraining)
        output = tf.nn.relu (output)
        
        output = tf.layers.conv2d_transpose(output, 32, [5, 5], strides = (2, 2), padding = "SAME", use_bias = False)
        output = tf.layers.batch_normalization(output, training = IsTraining)
        output = tf.nn.relu (output)
        
        output = tf.layers.conv2d_transpose(output, 1, [5, 5], strides = (1, 1), padding = "SAME", use_bias = False)
        output = tf.tanh (output)
        
    return output
 
# Discriminator Function
def Build_Discriminator (inputs, reuse = None):
    
    # 이하 Dirscriminator에 관여하는 모든 변수는 variable_scope로 묶어요.
    with tf.variable_scope("DiscriminatorVal") as scope:
        
        if reuse:
            scope.reuse_variables()
            
        output = tf.reshape (inputs, [-1, 28, 28, 1])
        output = tf.layers.conv2d(output, 32, [5, 5], strides = (2, 2), padding = "SAME", use_bias = True)
        output = tf.nn.leaky_relu (output)
        
        output = tf.layers.conv2d(output, 64, [5, 5], strides = (2, 2), padding = "SAME", use_bias = False)
        output = tf.layers.batch_normalization(output, training = IsTraining)
        output = tf.nn.leaky_relu (output)
        
        output = tf.layers.conv2d(output, 128, [5, 5], strides = (2, 2), padding = "SAME", use_bias = False)
        output = tf.layers.batch_normalization(output, training = IsTraining)
        output = tf.nn.leaky_relu (output)
        
        output = tf.layers.flatten(output)
        output = tf.layers.dense(output, 1, activation = None)
        
    return output
 
# 3. Noise Function
def Build_GetNoise (batch_size, noise_size):
    return np.random.uniform(-1.0, 1.0, size=[batch_size, noise_size])


# 데이터셋 전체를 학습에 사용할 횟수
# 데이터셋을 쪼갤 서브셋의 크기
# 노이즈의 크기
TotalEpoch= 50
BatchSize = 128
NoiseSize = 100

# Variable GeneratorVal/dense/kernel already exists, disallowed. 해결 방법
# tf.reset_default_graph()를 그래프 맨 앞에 적어두기
tf.reset_default_graph()
 
DiscriminatorInput = tf.placeholder(tf.float32, [None, 784])
GeneratorInput = tf.placeholder(tf.float32, [None, NoiseSize])
IsTraining = tf.placeholder(tf.bool)

DiscGlobalStep = tf.Variable(0, trainable = False, name = "DiscGlobal")
GeneGlobalStep = tf.Variable(0, trainable = False, name = "GeneGlobal")


# Step 1. Generator에 노이즈를 입력하여 가짜 이미지를 생성
# Step 2. Discriminator에 진짜 이미지 (MNIST)를 입력하여 Real 값을 추출
# Step 3. Discriminator의 변수를 고정하고 (reuse), 가짜 이미지를 Discriminator에 넣어서 Gene 값을 추출
# 진짜 이미지와 가짜 이미지가 판별기를 지났을때 추출한 output으로 Discriminator의 손실함수를 정의한다.
# Discriminator의 손실도는 이 둘을 더한 것으로서 수식적 형태로는 "log R + log (1-G)" 이다. DiscReal은 1, DiscGene은 0이 되도록 신경망을 경쟁시킨다.
FakeImage = Build_Generator(GeneratorInput)
DiscReal = Build_Discriminator(DiscriminatorInput)
DiscGene = Build_Discriminator(FakeImage, True)
 
# Loss1은 진짜 이미지가 만들어낸 손실도, Loss2는 가짜 이미지가 만들어낸 손실도
# 진짜 이미지일 가능성의 손실도 -> 1, 가짜 이미지일 가능성의 손실도 -> 0
DiscLoss1 = tf.reduce_mean(tf.nn.sigmoid_cross_entropy_with_logits(logits = DiscReal, labels = tf.ones_like(DiscReal)))
DiscLoss2 = tf.reduce_mean(tf.nn.sigmoid_cross_entropy_with_logits(logits = DiscGene, labels = tf.zeros_like(DiscGene)))

# Discriminator의 손실도는 두 입력이 만드는 손실도의 총합
# 생성된 가짜 이미지의 손실도 -> 1
DiscLoss = DiscLoss1 + DiscLoss2
GeneLoss = tf.reduce_mean(tf.nn.sigmoid_cross_entropy_with_logits(logits = DiscGene, labels = tf.ones_like(DiscGene)))



# tf.get_collection과 tf.GraphKeys.TRAINABLE_VARIABLES with "scope 이름" 을 이용하여 독립으로 학습시킨 변수들의 묶음을 정의한다.
# Discriminator의 변수와 Generator의 변수는 따로 학습시킨다.
# tf.control_dependecies는 묶음 연산과 실행 순서를 정의하는 메서드이다.
# UpdataOps를 먼저 실행하고 TrainDisc, TrainGene을 실행한다.
DiscVars = tf.get_collection (tf.GraphKeys.TRAINABLE_VARIABLES, scope = "DiscriminatorVal")
GeneVars = tf.get_collection (tf.GraphKeys.TRAINABLE_VARIABLES, scope = "GeneratorVal")
UpdateOps = tf.get_collection (tf.GraphKeys.UPDATE_OPS)

with tf.control_dependencies(UpdateOps):
    TrainDisc = tf.train.AdamOptimizer(learning_rate = 0.0010, beta1 = 0.9).minimize(DiscLoss, var_list=DiscVars, global_step = DiscGlobalStep)
    TrainGene = tf.train.AdamOptimizer(learning_rate = 0.0012, beta1 = 0.9).minimize(GeneLoss, var_list=GeneVars, global_step = GeneGlobalStep)

with tf.Session() as sess:
    sess.run(tf.global_variables_initializer())
    TotalBatch = int(mnist.train.num_examples / BatchSize)
    
    for epoch in range(TotalEpoch):
        
        DiscLossValue = 0
        GeneLossValue = 0
        
        for i in range(TotalBatch):
            
            batch_xs, batch_ys = mnist.train.next_batch(BatchSize)
            Noise = Build_GetNoise(BatchSize, NoiseSize)

            # Discriminator는 원본 이미지와 노이즈가 생성한 이미지를 모두 받은 후에 학습하여서 feed_dict가 X, Z 둘 다 필요
            sess.run(TrainDisc, feed_dict = {DiscriminatorInput : batch_xs, GeneratorInput : Noise, IsTraining : True})
            DiscLossValue = sess.run(DiscLoss, feed_dict = {DiscriminatorInput : batch_xs, GeneratorInput : Noise, IsTraining : True})
            
            # Generator는 원본 이미지가 관여하지 않아요. 오직 노이즈만 받으면 됩니다.
            sess.run(TrainGene, feed_dict = {DiscriminatorInput : batch_xs, GeneratorInput : Noise, IsTraining : True})
            GeneLossValue = sess.run(GeneLoss, feed_dict = {DiscriminatorInput : batch_xs, GeneratorInput : Noise, IsTraining : True})

        print('Epoch:', '%02d   ' %(epoch+1), 'D loss: {:.4}   '.format(DiscLossValue), 'G loss: {:.4}   '.format(GeneLossValue))

        if epoch % 1 == 0:
            
            Noise = Build_GetNoise(10, NoiseSize)
            Samples = sess.run(FakeImage, feed_dict = {GeneratorInput : Noise, IsTraining : False})

            
            fig, ax = plt.subplots(1, 10, figsize=(20, 10))

            for i in range(10):
                ax[i].set_axis_off()
                ax[i].imshow(np.reshape(Samples[i], (28, 28)))

            plt.show ()
            plt.close(fig)