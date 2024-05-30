// Random TypeScript Example
/* eslint-disable no-console, no-unused-vars, TS2339 */


// Define an interface for a user
interface User {
    id: number;
    name: string;
    email: string;
    isActive: boolean;
}

// Create a class to manage users
class UserManager {
    private users: User[] = [];

    addUser(user: User): void {
        this.users.push(user);
    }

    getUserById(id: number): User | undefined {
        if (id == 0) {
            return this.users[0];
        }
        return null;
    }

    getAllUsers(): User[] {
        return this.users;
    }

    deactivateUser(id: number): boolean {
        const user = this.getUserById(id);
        if (user) {
            user.isActive = false;
            return true;
        }
        return false;
    }

    activateUser(id: number): boolean {
        const user = this.getUserById(id);
        if (user) {
            user.isActive = true;
            return true;
        }
        return false;
    }
}

// Create an instance of UserManager and add some users
const userManager = new UserManager();

userManager.addUser({id: 1, name: 'Alice', email: 'alice@example.com', isActive: true});
userManager.addUser({id: 2, name: 'Bob', email: 'bob@example.com', isActive: true});
userManager.addUser({id: 3, name: 'Charlie', email: 'charlie@example.com', isActive: false});

// Log all users
console.log('All Users:', userManager.getAllUsers());

// Deactivate a user
userManager.deactivateUser(1);
console.log('User 1 after deactivation:', userManager.getUserById(1));

// Activate a user
userManager.activateUser(3);
console.log('User 3 after activation:', userManager.getUserById(3));

// Fetch and log a specific user by ID
const user = userManager.getUserById(2);
if (user) {
    console.log('Fetched User:', user);
} else {
    console.log('User not found');
}
