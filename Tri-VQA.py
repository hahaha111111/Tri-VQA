class Tri_VQA(torch.nn.Module): 
    def __init__(self):
        super(Tri_VQA, self).__init__()
        self.question_dim = 768  # Dimension of BERT embeddings
        self.image_dim = 512  # Dimension of CLIP embeddings
        self.hidden_dim = 2048

        self.fc = torch.nn.Sequential(
            torch.nn.Linear(self.image_dim + self.question_dim, self.hidden_dim),
            torch.nn.Linear(self.hidden_dim, self.hidden_dim),
            torch.nn.Linear(self.hidden_dim, 545)
        )

        self.feature_extractor = CLIP()  # CLIP model for image feature extraction
        self.question_feature = BERT()  # BERT model for question feature extraction
        self.answer_feature = nn.LSTM(1, self.hidden_dim, 2)

        self.fe_layers = torch.nn.ModuleList([
            torch.nn.Sequential(torch.nn.Linear(self.hidden_dim, self.hidden_dim))
            for _ in range(17)
        ])

        self.fv_layers = torch.nn.ModuleList([
            torch.nn.Sequential(torch.nn.Linear(self.hidden_dim, self.hidden_dim))
            for _ in range(17)
        ])

    def forward(self, image, question, questionTypeIdx):
        image_feature = self.feature_extractor(image)  # 64, 512

        question_embedding = self.question_feature(question)  # 64, 768

        # Resize question embedding to match image feature dimension
        question_feature = question_embedding.unsqueeze(1).expand(-1, self.image_dim)  # 64, 512

        # Combine image and question features
        combined_feature = torch.cat((image_feature, question_feature), dim=1)  # 64, 1024

        label_answer = self.fc(combined_feature)  # 64, 545

        answer_feature = []
        for index in range(len(image)):
            b = torch.argmax(label_answer, dim=1)[index]
            number = find(b.item())  # Function to find the answer index
            a = answer_global[number][b.item() - list[number]]  # Answer corresponding to the index
            c = BERT(a)  # BERT embedding for answer
            c = c[:, 0, :]  # Take the first token's embedding
            answer_feature.append(self.answer_feature(c)[0][-1, :, :])

        answer_feature = torch.stack(answer_feature)
        answer_feature_cycle = torch.cat((answer_feature.squeeze(dim=1), image_feature), dim=1)
        vision_feature_cycle = torch.cat((answer_feature.squeeze(dim=1), question_feature), dim=1)

        answer_feature_pre = []
        for i in range(len(image)):
            answer_feature_pre_i = self.fe_layers[questionTypeIdx[i].item()](answer_feature_cycle[i])
            answer_feature_pre.append(answer_feature_pre_i)

        answer_feature_pre = torch.stack(answer_feature_pre)
        prob3 = image_feature + answer_feature_pre  # 64, 512
        label_answer_q = self.fc(prob3)

        vision_feature_pre = []
        for i in range(len(image)):
            vision_feature_pre_i = self.fv_layers[questionTypeIdx[i].item()](vision_feature_cycle[i])
            vision_feature_pre.append(vision_feature_pre_i)

        vision_feature_pre = torch.stack(vision_feature_pre)
        prob2 = vision_feature_pre + question_feature  # 64, 512
        label_answer_v = self.fc(prob2)

        return label_answer, label_answer_v, label_answer_q, answer_feature_pre, question_feature, vision_feature_pre, image_feature
