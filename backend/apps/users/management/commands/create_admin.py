from apps.users.models import User; 

User.objects.create_user(
    username='admin',
    email='mervedienkouka@gmail.com',
    password='2006@MNK', 
    role=User.Roles.ADMIN);
print('admin cree')