from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

import tensorflow as tf
import numpy as np

import sys
import time

import cogan_model as cogan

sys.path.append('../')
import image_utils as iu
from datasets import MNISTDataSet as DataSet


results = {
    'output': './gen_img/',
    'model': './model/CoGAN-model.ckpt'
}

train_step = {
    'batch_size': 128,
    'global_step': 12500,
    'logging_interval': 250,
}


def main():
    start_time = time.time()  # Clocking start

    # MNIST Dataset load
    mnist = DataSet(ds_path="D:\\DataSet/mnist/").data

    # GPU configure
    config = tf.ConfigProto()
    config.gpu_options.allow_growth = True

    with tf.Session(config=config) as s:
        # CoGAN Model
        model = cogan.CoGAN(s, batch_size=train_step['batch_size'])

        # Load model & Graph & Weights
        saved_global_step = 0
        ckpt = tf.train.get_checkpoint_state('./model/')
        if ckpt and ckpt.model_checkpoint_path:
            # Restores from checkpoint
            model.saver.restore(s, ckpt.model_checkpoint_path)

            saved_global_step = int(ckpt.model_checkpoint_path.split('/')[-1].split('-')[-1])
            print("[+] global step : %d" % saved_global_step, " successfully loaded")
        else:
            print('[-] No checkpoint file found')

        # Initializing
        s.run(tf.global_variables_initializer())

        sample_y = np.zeros(shape=[model.sample_num, model.n_classes])
        for i in range(10):
            sample_y[10 * i:10 * (i + 1), i] = 1

        for global_step in range(saved_global_step, train_step['global_step']):
            batch_x, batch_y = mnist.train.next_batch(model.batch_size)
            # batch_rot_x = np.reshape(np.rot90(np.reshape(batch_x, model.image_shape), 1), (-1, 784))
            batch_z = np.random.uniform(-1., 1., [model.batch_size, model.z_dim]).astype(np.float32)

            # Update D network
            _, d_loss = s.run([model.d_op, model.d_loss],
                              feed_dict={
                                  model.x_1: batch_x,
                                  model.x_2: batch_x,  # batch_rot_x
                                  # model.y: batch_y,
                                  model.z: batch_z,
                              })

            # Update G network
            _, g_loss = s.run([model.g_op, model.g_loss],
                              feed_dict={
                                  model.x_1: batch_x,
                                  model.x_2: batch_x,
                                  # model.y: batch_y,
                                  model.z: batch_z,
                              })

            if global_step % train_step['logging_interval'] == 0:
                batch_x, batch_y = mnist.train.next_batch(model.batch_size)
                # batch_rot_x = np.reshape(np.rot90(np.reshape(batch_x, model.image_shape), 1), (-1, 784))
                batch_z = np.random.uniform(-1., 1., [model.batch_size, model.z_dim]).astype(np.float32)

                d_loss, g_loss, summary = s.run([model.d_loss, model.g_loss, model.merged],
                                                feed_dict={
                                                    model.x_1: batch_x,
                                                    model.x_2: batch_x,
                                                    # model.y: batch_y,
                                                    model.z: batch_z,
                                                })

                # Print loss
                print("[+] Step %08d => " % global_step,
                      " D loss : {:.8f}".format(d_loss),
                      " G loss : {:.8f}".format(g_loss))

                # Training G model with sample image and noise
                sample_z = np.random.uniform(-1., 1., [model.sample_num, model.z_dim]).astype(np.float32)
                samples_1 = s.run(model.g_sample_1,
                                  feed_dict={
                                      # model.y: sample_y,
                                      model.z: sample_z,
                                  })
                samples_2 = s.run(model.g_sample_2,
                                  feed_dict={
                                      # model.y: sample_y,
                                      model.z: sample_z,
                                  })

                # Summary saver
                model.writer.add_summary(summary, global_step)

                # Export image generated by model G
                sample_image_height = model.sample_size
                sample_image_width = model.sample_size

                sample_dir_1 = results['output'] + 'train_1_{:08d}.png'.format(global_step)
                sample_dir_2 = results['output'] + 'train_2_{:08d}.png'.format(global_step)

                # Generated image save
                iu.save_images(samples_1,
                               size=[sample_image_height, sample_image_width],
                               image_path=sample_dir_1)
                iu.save_images(samples_2,
                               size=[sample_image_height, sample_image_width],
                               image_path=sample_dir_2)

                # Model save
                model.saver.save(s, results['model'], global_step)

    end_time = time.time() - start_time  # Clocking end

    # Elapsed time
    print("[+] Elapsed time {:.8f}s".format(end_time))

    # Close tf.Session
    s.close()


if __name__ == '__main__':
    main()