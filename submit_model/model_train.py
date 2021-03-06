from datetime import datetime
import time
import math

import tensorflow as tf

import model

FLAGS = tf.app.flags.FLAGS

tf.app.flags.DEFINE_string('train_dir', './model_train',
                           """Directory where to write event logs """
                           """and checkpoint.""")
tf.app.flags.DEFINE_integer('max_steps', 1000000,
                            """Number of batches to run.""")
tf.app.flags.DEFINE_boolean('log_device_placement', False,
                            """Whether to log device placement.""")
tf.app.flags.DEFINE_integer('log_frequency', 10,
                            """How often to log results to the console.""")


def train():
    with tf.Graph().as_default():
        global_step = tf.train.get_or_create_global_step()

        with tf.device('/cpu:0'):
            images, labels = model.inputs(False)

        logits = model.inference(images)

        loss = model.loss(logits, labels)

        train_op = model.train(loss, global_step)

        class _LoggerHook(tf.train.SessionRunHook):

            def begin(self):
                self._step = -1
                self._start_time = time.time()

            def before_run(self, run_context):
                self._step += 1
                return tf.train.SessionRunArgs(loss)    # Asks for loss value.

            def after_run(self, run_context, run_values):
                if self._step % FLAGS.log_frequency == 0:
                    current_time = time.time()
                    duration = current_time - self._start_time
                    self._start_time = current_time

                    loss_value = run_values.results
                    examples_per_sec = FLAGS.log_frequency * FLAGS.batch_size / duration
                    sec_per_batch = float(duration / FLAGS.log_frequency)

                    format_str = ('%s: step %d, loss = %.2f (%.1f examples/sec; %.3f '
                                  'sec/batch)')
                    print (format_str % (datetime.now(), self._step, loss_value,
                                         examples_per_sec, sec_per_batch))

        class _EarlyStoppingHook(tf.train.SessionRunHook):

            def __init__(self, loss_thresh, steps_thresh):
                self.loss_thresh = loss_thresh
                self.steps_thresh = steps_thresh

            def begin(self):
                self.curr_steps = -1
                self.curr_loss = math.inf
                    
            def before_run(self, run_context):
                        self.curr_steps += 1
                        return tf.train.SessionRunArgs(loss)

            def after_run(self, run_context, run_values):
                loss_value = run_values.results
                if self.curr_loss - loss_value > self.loss_thresh:
                    self.curr_loss = loss_value
                    self.curr_steps = 0
                elif self.curr_steps > self.steps_thresh:
                    print("Finished training by early stopping")
                    raise StopIteration

        with tf.train.MonitoredTrainingSession(
                checkpoint_dir=FLAGS.train_dir,
                hooks=[tf.train.StopAtStepHook(last_step=FLAGS.max_steps),
                       tf.train.NanTensorHook(loss),
                       _LoggerHook(),
                       _EarlyStoppingHook(1e-1, 100)],
                config=tf.ConfigProto(
                    log_device_placement=FLAGS.log_device_placement)
        ) as mon_sess:
            while not mon_sess.should_stop():
                mon_sess.run(train_op)


def main(argv=None):    # pylint: disable=unused-argument
    train()


if __name__ == '__main__':
    tf.app.run()
