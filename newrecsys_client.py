# -*- coding: utf-8 -*-
"""NewRecSys_client.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1EkuSfLgIzT583V3k-PiXjhol9Y8Y8nvB
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import sys
import kubernetes

import numpy as np
import tensorflow as tf


def _parse_task_name_fn(load_balancer_name):
  """Parses task type and id from a service name."""
  splits = load_balancer_name.split('-')
  if len(splits) <= 3:
    raise ValueError(
        "Could recognize load_balancer's name: %r" % load_balancer_name)
  task_type = splits[-2]
  if task_type not in ['chief', 'worker', 'ps', 'evaluator']:
    return None, None
  task_id = int(splits[-1])
  assert task_id >= 0
  return task_type, task_id


def resolve_cluster(port=5000, parse_task_name_fn=_parse_task_name_fn):
  """Queries Kubernetes cluster and gets cluster_spec."""
  kubernetes.config.load_kube_config()
  v1 = kubernetes.client.CoreV1Api()
  ret = v1.list_service_for_all_namespaces()
  cluster_spec = {}
  for item in ret.items:
    if item.status.load_balancer and item.status.load_balancer.ingress:
      task_type, task_id = parse_task_name_fn(item.metadata.name)
      if not task_type:
        continue
      if task_type not in cluster_spec:
        cluster_spec[task_type] = []
      while len(cluster_spec[task_type]) <= task_id:
        cluster_spec[task_type].append(None)
      cluster_spec[task_type][task_id] = '%s:%d' % (
          item.status.load_balancer.ingress[0].ip, port)

  if not cluster_spec:
    raise ValueError(
        "Cannot get cluster_spec. It's possible the cluster is not ready.")
  for task_type, targets in cluster_spec.items():
    for target in targets:
      if target is None:
        raise ValueError(
            'Not all %s tasks are found in the cluster' % task_type)
  tf.logging.info('Using cluster_spec %r' % cluster_spec)
  return cluster_spec

def main(args):

  #Added
  def input_fn(eval):

    if eval == 0:
      x = train_x
      y = train_y
    else:
      x = test_x
      y = test_y

    x = tf.cast(x, tf.float32)
    dataset = tf.data.Dataset.from_tensor_slices((x, y))
    dataset = dataset.repeat(100)
    dataset = dataset.batch(32)
    return dataset
  #-------------------------## 

  if len(args) < 2:
    print('You must specify model_dir for checkpoints such as'
          ' /tmp/tfkeras_example/.')
    return

  model_dir = args[1]
  print('Using %s to store checkpoints.' % model_dir)

  (training_data, training_targets), (testing_data, testing_targets) = imdb.load_data(num_words=10000)
  data = np.concatenate((training_data, testing_data), axis=0)
  targets = np.concatenate((training_targets, testing_targets), axis=0)

  def vectorize(sequences, dimension = 10000):
    results = np.zeros((len(sequences), dimension))
    for i, sequence in enumerate(sequences):
      results[i, sequence] = 1
    return results
  
  data = vectorize(data)
  targets = np.array(targets).astype("float32")
  test_x = data[:10000]
  test_y = targets[:10000]
  train_x = data[10000:]
  train_y = targets[10000:]


  model = tf.keras.Sequential()
  # Input - Layer
  model.add(keras.layers.Dense(50, activation = "relu", input_shape=(10000, )))

  # Hidden - Layers
  model.add(keras.layers.Dropout(0.3, noise_shape=None, seed=None))
  model.add(keras.layers.Dense(50, activation = "relu"))
  model.add(keras.layers.Dropout(0.2, noise_shape=None, seed=None))
  model.add(keras.layers.Dense(50, activation = "relu"))

  # Output- Layer
  model.add(keras.layers.Dense(1, activation = "sigmoid"))
  model.summary()

  # Compile the model.
  optimizer = tf.train.GradientDescentOptimizer(0.2)
  model.compile(loss='binary_crossentropy', optimizer=optimizer)
  model.summary()
  tf.keras.backend.set_learning_phase(True)

  results = model.fit(
  train_x, train_y,
  epochs= 2,
  batch_size = 500,
  validation_data = (test_x, test_y),
  use_multiprocessing=True
  )
  results.history


  #Added
  # Define DistributionStrategies and convert the Keras Model to an
  # Estimator that utilizes these DistributionStrateges.
  # Evaluator is a single worker, so using MirroredStrategy.
  config = tf.estimator.RunConfig(
      experimental_distribute=tf.contrib.distribute.DistributeConfig(
          train_distribute=tf.contrib.distribute.CollectiveAllReduceStrategy(
              num_gpus_per_worker=2),
          eval_distribute=tf.contrib.distribute.MirroredStrategy(
              num_gpus_per_worker=2)))
  keras_estimator = tf.keras.estimator.model_to_estimator(
      keras_model=model, config=config, model_dir=model_dir)
    
  # Train and evaluate the model. Evaluation will be skipped if there is not an
  # "evaluator" job in the cluster.
  tf.estimator.train_and_evaluate(
      keras_estimator,
      train_spec=tf.estimator.TrainSpec(input_fn=input_fn(0)),
      eval_spec=tf.estimator.EvalSpec(input_fn=input_fn(1)))

  #----------------------------------------------------------#

  if __name__ == '__main__':
    tf.logging.set_verbosity(tf.logging.INFO)
    tf.app.run(argv=sys.argv)