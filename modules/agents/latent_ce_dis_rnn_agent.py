import torch.nn as nn
import torch.nn.functional as F
import torch as th
from torch.distributions import kl_divergence
import torch.distributions as D
import math
from tensorboardX import SummaryWriter
import time
import matplotlib.pyplot as plt


class LatentCEDisRNNAgent(nn.Module):
    def __init__(self, input_shape, args):
        super(LatentCEDisRNNAgent, self).__init__()
        self.args = args
        self.input_shape = input_shape
        self.n_agents = args.n_agents
        self.n_actions = args.n_actions
        self.latent_dim = args.latent_dim
        self.hidden_dim = args.rnn_hidden_dim
        self.bs = args.batch_size_run
        self.embed_fc_input_size = input_shape
        NN_HIDDEN_SIZE = args.NN_HIDDEN_SIZE
        activation_func = nn.LeakyReLU()

        self.embed_net = nn.Sequential(nn.Linear(self.embed_fc_input_size, NN_HIDDEN_SIZE),
                                       nn.BatchNorm1d(NN_HIDDEN_SIZE),
                                       activation_func,
                                       nn.Linear(NN_HIDDEN_SIZE, args.latent_dim * 2))

        self.inference_net = nn.Sequential(nn.Linear(args.rnn_hidden_dim + input_shape, NN_HIDDEN_SIZE),
                                           nn.BatchNorm1d(NN_HIDDEN_SIZE),
                                           activation_func,
                                           nn.Linear(NN_HIDDEN_SIZE, args.latent_dim * 2))

        self.latent = th.rand(args.n_agents, args.latent_dim * 2)  # (n,mu+var)
        self.latent_infer = th.rand(args.n_agents, args.latent_dim * 2)  # (n,mu+var)

        self.latent_net = nn.Sequential(nn.Linear(args.latent_dim, NN_HIDDEN_SIZE),
                                        nn.BatchNorm1d(NN_HIDDEN_SIZE),
                                        activation_func)

        self.fc1 = nn.Linear(input_shape, args.rnn_hidden_dim)
        self.rnn = nn.GRUCell(args.rnn_hidden_dim, args.rnn_hidden_dim)

        self.fc2_w_nn = nn.Linear(NN_HIDDEN_SIZE, args.rnn_hidden_dim * args.n_actions)
        self.fc2_b_nn = nn.Linear(NN_HIDDEN_SIZE, args.n_actions)

        # Dis Net
        self.dis_net = nn.Sequential(nn.Linear(args.latent_dim * 2, NN_HIDDEN_SIZE),
                                     nn.BatchNorm1d(NN_HIDDEN_SIZE),
                                     activation_func,
                                     nn.Linear(NN_HIDDEN_SIZE, 1))

        self.mi = th.rand(args.n_agents * args.n_agents)
        self.dissimilarity = th.rand(args.n_agents * args.n_agents)

        if args.dis_sigmoid:
            print('>>> sigmoid')
            self.dis_loss_weight_schedule = self.dis_loss_weight_schedule_sigmoid
        else:
            self.dis_loss_weight_schedule = self.dis_loss_weight_schedule_step

    def init_latent(self, bs):
        self.bs = bs
        loss = 0

        # if self.args.runner == "episode":
        #     self.writer = SummaryWriter(
        #         "results/tb_logs/test_latent-" + time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime()))
        self.trajectory = []

        var_mean = self.latent[:self.n_agents, self.args.latent_dim:].detach().mean()

        mi = self.mi
        di = self.dissimilarity
        indicator = [var_mean, mi.max(), mi.min(), mi.mean(), mi.std(), di.max(), di.min(), di.mean(), di.std()]
        return indicator, self.latent[:self.n_agents, :].detach(), self.latent_infer[:self.n_agents, :].detach()

    def init_hidden(self):
        # make hidden states on same device as model
        return self.fc1.weight.new(1, self.args.rnn_hidden_dim).zero_()

    def forward(self, inputs, hidden_state, t=0, batch=None, test_mode=None, t_glob=0, train_mode=False):
        inputs = inputs.reshape(-1, self.input_shape)
        h_in = hidden_state.reshape(-1, self.hidden_dim)

        embed_fc_input = inputs[:, - self.embed_fc_input_size:]  # own features(unit_type_bits+shield_bits_ally)+id

        self.latent = self.embed_net(embed_fc_input)
        self.latent[:, -self.latent_dim:] = th.clamp(th.exp(self.latent[:, -self.latent_dim:]),
                                                     min=self.args.var_floor)  # var
        size = self.latent.shape[0] * self.latent.shape[1] / (self.latent_dim * 2)
        latent_embed = self.latent.reshape(int(size), self.latent_dim * 2)

        gaussian_embed = D.Normal(latent_embed[:, :self.latent_dim], (latent_embed[:, self.latent_dim:]) ** (1 / 2))
        latent = gaussian_embed.rsample()

        # x0, y0, z0, x1, y1, z1, x2, y2, z2 = [], [], [], [], [], [], [], [], []
        #
        # if t % 80 == 0:
        #     x0.append(latent[0, 0].detach().cpu())
        #     y0.append(latent[0, 1].detach().cpu())
        #     z0.append(latent[0, 2].detach().cpu())
        #     x1 = latent[1:3, 0].detach().cpu()
        #     y1 = latent[1:3, 1].detach().cpu()
        #     z1 = latent[1:3, 2].detach().cpu()
        #     x2 = latent[3:, 0].detach().cpu()
        #     y2 = latent[3:, 1].detach().cpu()
        #     z2 = latent[3:, 2].detach().cpu()
        #     fig = plt.figure(figsize=(16, 12))
        #     ax = plt.axes(projection="3d")
        #     # Add x, and y gridlines for the figure
        #     ax.grid(b=True, color='blue', linestyle='-.', linewidth=0.5, alpha=0.3)
        #     # Creating the color map for the plot
        #     my_cmap = plt.get_cmap('hsv')
        #     # Creating the 3D plot
        #     sctt = ax.scatter3D(x0, y0, z0, c='b', alpha=0.8, marker='.', s=500) #* r
        #     sctt = ax.scatter3D(x1, y1, z1, c='b', alpha=0.8, marker='.', s=500) #^ b
        #     sctt = ax.scatter3D(x2, y2, z2, c='b', alpha=0.8, marker='.', s=500) #g
        #     # display the plot
        #     # plt.show()
        #     plt.savefig(r'C:\Users\pp\WorkFiles\experiment\smac\SMAC_baselines\SMAC-master-HAVEN\1.pdf')
        #     plt.close()

        c_dis_loss = th.tensor(0.0).to(self.args.device)
        ce_loss = th.tensor(0.0).to(self.args.device)
        loss = th.tensor(0.0).to(self.args.device)

        if train_mode and (not self.args.roma_raw):
            self.latent_infer = self.inference_net(th.cat([h_in.detach(), inputs], dim=1))
            self.latent_infer[:, -self.latent_dim:] = th.clamp(th.exp(self.latent_infer[:, -self.latent_dim:]),
                                                               min=self.args.var_floor)
            gaussian_infer = D.Normal(self.latent_infer[:, :self.latent_dim],
                                      (self.latent_infer[:, self.latent_dim:]) ** (1 / 2))
            latent_infer = gaussian_infer.rsample()

            loss = gaussian_embed.entropy().sum(dim=-1).mean() * self.args.h_loss_weight + kl_divergence(gaussian_embed,
                                                                                                         gaussian_infer).sum(
                dim=-1).mean() * self.args.kl_loss_weight  # CE = H + KL
            loss = th.clamp(loss, max=2e3)
            ce_loss = th.log(1 + th.exp(loss))

            # Dis Loss
            cur_dis_loss_weight = self.dis_loss_weight_schedule(t_glob)
            if cur_dis_loss_weight > 0:
                dis_loss = 0
                dissimilarity_cat = None
                mi_cat = None
                latent_dis = latent.clone().view(self.bs, self.n_agents, -1)
                latent_move = latent.clone().view(self.bs, self.n_agents, -1)
                for agent_i in range(self.n_agents):
                    latent_move = th.cat(
                        [latent_move[:, -1, :].unsqueeze(1), latent_move[:, :-1, :]], dim=1)
                    latent_dis_pair = th.cat([latent_dis[:, :, :self.latent_dim],
                                              latent_move[:, :, :self.latent_dim],
                                              ], dim=2)
                    mi = th.clamp(gaussian_embed.log_prob(latent_move.view(self.bs * self.n_agents, -1)) + 13.9,
                                  min=-13.9).sum(dim=1, keepdim=True) / self.latent_dim

                    dissimilarity = th.abs(self.dis_net(latent_dis_pair.view(-1, 2 * self.latent_dim)))

                    if dissimilarity_cat is None:
                        dissimilarity_cat = dissimilarity.view(self.bs, -1).clone()
                    else:
                        dissimilarity_cat = th.cat([dissimilarity_cat, dissimilarity.view(self.bs, -1)], dim=1)
                    if mi_cat is None:
                        mi_cat = mi.view(self.bs, -1).clone()
                    else:
                        mi_cat = th.cat([mi_cat, mi.view(self.bs, -1)], dim=1)

                mi_min = mi_cat.min(dim=1, keepdim=True)[0]
                mi_max = mi_cat.max(dim=1, keepdim=True)[0]
                di_min = dissimilarity_cat.min(dim=1, keepdim=True)[0]
                di_max = dissimilarity_cat.max(dim=1, keepdim=True)[0]

                mi_cat = (mi_cat - mi_min) / (mi_max - mi_min + 1e-12)
                dissimilarity_cat = (dissimilarity_cat - di_min) / (di_max - di_min + 1e-12)

                dis_loss = - th.clamp(mi_cat + dissimilarity_cat, max=1.0).sum() / self.bs / self.n_agents
                dis_norm = th.norm(dissimilarity_cat, p=1, dim=1).sum() / self.bs / self.n_agents

                c_dis_loss = (
                                     dis_norm + self.args.soft_constraint_weight * dis_loss) / self.n_agents * cur_dis_loss_weight
                loss = ce_loss + c_dis_loss

                self.mi = mi_cat[0]
                self.dissimilarity = dissimilarity_cat[0]
            else:
                c_dis_loss = th.zeros_like(loss)
                loss = ce_loss

        # Role -> FC2 Params
        latent = self.latent_net(latent)

        fc2_w = self.fc2_w_nn(latent)
        fc2_b = self.fc2_b_nn(latent)
        fc2_w = fc2_w.reshape(-1, self.args.rnn_hidden_dim, self.args.n_actions)
        fc2_b = fc2_b.reshape((-1, 1, self.args.n_actions))

        x = F.relu(self.fc1(inputs))  # (bs*n,(obs+act+id)) at time t
        h = self.rnn(x, h_in)
        h = h.reshape(-1, 1, self.args.rnn_hidden_dim)
        q = th.bmm(h, fc2_w) + fc2_b

        h = h.reshape(-1, self.args.rnn_hidden_dim)

        # if self.args.runner == "episode":
        #     self.writer.add_embedding(self.latent.reshape(-1, self.latent_dim * 2), list(range(self.args.n_agents)),
        #                               global_step=t, tag="latent-cur")
        #     self.writer.add_embedding(self.latent_infer.reshape(-1, self.latent_dim * 2),
        #                               list(range(self.args.n_agents)),
        #                               global_step=t, tag="latent-hist")

        return q.view(-1, self.args.n_actions), h.view(-1, self.args.rnn_hidden_dim), loss, c_dis_loss, ce_loss

    def dis_loss_weight_schedule_step(self, t_glob):
        if t_glob > self.args.dis_time:
            return self.args.dis_loss_weight
        else:
            return 0

    def dis_loss_weight_schedule_sigmoid(self, t_glob):
        return self.args.dis_loss_weight / (1 + math.exp((1e7 - t_glob) / 2e6))
